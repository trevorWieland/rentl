"""Protocol definitions and errors for export adapters."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.events import (
    ExportCompletedData,
    ExportEvent,
    ExportFailedData,
    ExportStartedData,
)
from rentl_schemas.io import ExportTarget, TranslatedLine
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import (
    FileFormat,
    LogLevel,
    PhaseName,
    RunId,
    Timestamp,
)
from rentl_schemas.responses import ErrorDetails, ErrorResponse


class ExportErrorCode(StrEnum):
    """Categorized error codes for export failures."""

    INVALID_FORMAT = "invalid_format"
    VALIDATION_ERROR = "validation_error"
    IO_ERROR = "io_error"
    UNTRANSLATED_TEXT = "untranslated_text"
    DROPPED_COLUMN = "dropped_column"


class ExportErrorDetails(BaseSchema):
    """Detailed export error context."""

    field: str | None = Field(None, description="Field associated with the error")
    row_number: int | None = Field(
        None, ge=1, description="CSV row number if applicable"
    )
    line_number: int | None = Field(None, ge=1, description="Line number if applicable")
    column_name: str | None = Field(None, description="Column name if applicable")
    provided: str | None = Field(None, description="Provided value if available")
    valid_options: list[str] | None = Field(
        None, description="Valid options if applicable"
    )
    output_path: str | None = Field(None, description="Output file path")
    expected_fields: list[str] | None = Field(
        None, description="Expected field names for the record"
    )
    example: str | None = Field(None, description="Example output snippet for guidance")


class ExportErrorInfo(BaseSchema):
    """Structured export error data."""

    code: ExportErrorCode = Field(..., description="Export error code")
    message: str = Field(..., min_length=1, description="Error message")
    details: ExportErrorDetails | None = Field(None, description="Error details")

    def to_error_response(self) -> ErrorResponse:
        """Convert export error info to the standard error response schema.

        Returns:
            ErrorResponse: Standard response error payload.
        """
        details: ErrorDetails | None = None
        if self.details is not None:
            details = ErrorDetails(
                field=self.details.field,
                provided=self.details.provided,
                valid_options=self.details.valid_options,
            )

        message = self.message
        location = _format_location(self.details)
        if location is not None:
            message = f"{location}: {message}"

        code_value = getattr(self.code, "value", self.code)
        return ErrorResponse(code=str(code_value), message=message, details=details)


class ExportError(Exception):
    """Export error with structured details."""

    def __init__(self, info: ExportErrorInfo) -> None:
        """Initialize the export error.

        Args:
            info: Structured export error information.
        """
        super().__init__(info.message)
        self.info = info


class ExportBatchError(Exception):
    """Export error containing multiple issues."""

    def __init__(self, errors: list[ExportErrorInfo]) -> None:
        """Initialize the batch export error.

        Args:
            errors: Collected export errors.
        """
        super().__init__(f"{len(errors)} export errors")
        self.errors = errors


@runtime_checkable
class ExportAdapterProtocol(Protocol):
    """Protocol for export adapters."""

    format: FileFormat

    async def write_output(
        self, target: ExportTarget, lines: list[TranslatedLine]
    ) -> ExportResult:
        """Write translated lines to the export target.

        Raises:
            ExportError: For fatal export errors.
            ExportBatchError: For per-record validation issues.
        """
        raise NotImplementedError


class ExportSummary(BaseSchema):
    """Summary information for export output."""

    output_path: str = Field(..., min_length=1, description="Export output path")
    format: FileFormat = Field(..., description="Export output format")
    line_count: int = Field(..., ge=0, description="Number of lines exported")
    untranslated_count: int = Field(
        ..., ge=0, description="Number of untranslated lines detected"
    )
    column_count: int | None = Field(
        None, ge=0, description="Number of CSV columns if applicable"
    )
    columns: list[str] | None = Field(
        None, description="CSV columns used in the export if applicable"
    )


class ExportResult(BaseSchema):
    """Result information for export execution."""

    summary: ExportSummary = Field(..., description="Export summary")
    warnings: list[ExportErrorInfo] | None = Field(
        None, description="Optional export warnings"
    )


def build_export_started_log(
    timestamp: Timestamp, run_id: RunId, target: ExportTarget
) -> LogEntry:
    """Build a log entry for export start.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        target: Export target descriptor.

    Returns:
        LogEntry: Structured export log entry.
    """
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=ExportEvent.STARTED,
        run_id=run_id,
        phase=PhaseName.EXPORT,
        message="Export started",
        data=ExportStartedData(
            output_path=target.output_path,
            format=target.format,
        ).model_dump(exclude_none=True),
    )


def build_export_completed_log(
    timestamp: Timestamp,
    run_id: RunId,
    target: ExportTarget,
    line_count: int,
    untranslated_count: int | None = None,
    column_count: int | None = None,
) -> LogEntry:
    """Build a log entry for export completion.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        target: Export target descriptor.
        line_count: Number of lines exported.
        untranslated_count: Optional untranslated line count.
        column_count: Optional CSV column count.

    Returns:
        LogEntry: Structured export log entry.
    """
    data = ExportCompletedData(
        output_path=target.output_path,
        format=target.format,
        line_count=line_count,
        untranslated_count=untranslated_count,
        column_count=column_count,
    ).model_dump(exclude_none=True)

    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=ExportEvent.COMPLETED,
        run_id=run_id,
        phase=PhaseName.EXPORT,
        message="Export completed",
        data=data,
    )


def build_export_failed_log(
    timestamp: Timestamp,
    run_id: RunId,
    target: ExportTarget,
    error: ExportErrorInfo,
    error_count: int | None = None,
) -> LogEntry:
    """Build a log entry for export failure.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        target: Export target descriptor.
        error: Primary export error information.
        error_count: Optional total number of errors.

    Returns:
        LogEntry: Structured export log entry.
    """
    data = ExportFailedData(
        output_path=target.output_path,
        format=target.format,
        error_code=str(error.code),
        error_message=error.message,
        error_count=error_count,
    ).model_dump(exclude_none=True)

    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.ERROR,
        event=ExportEvent.FAILED,
        run_id=run_id,
        phase=PhaseName.EXPORT,
        message="Export failed",
        data=data,
    )


def _format_location(details: ExportErrorDetails | None) -> str | None:
    if details is None:
        return None
    if details.row_number is not None:
        return f"row {details.row_number}"
    if details.line_number is not None:
        return f"line {details.line_number}"
    return None
