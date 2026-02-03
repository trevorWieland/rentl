"""Protocol definitions and errors for ingest adapters."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.events import (
    IngestCompletedData,
    IngestEvent,
    IngestFailedData,
    IngestStartedData,
)
from rentl_schemas.io import IngestSource, SourceLine
from rentl_schemas.logs import LogEntry
from rentl_schemas.primitives import (
    FileFormat,
    LogLevel,
    PhaseName,
    RunId,
    Timestamp,
)
from rentl_schemas.responses import ErrorDetails, ErrorResponse


class IngestErrorCode(StrEnum):
    """Categorized error codes for ingest failures."""

    INVALID_FORMAT = "invalid_format"
    PARSE_ERROR = "parse_error"
    MISSING_FIELD = "missing_field"
    VALIDATION_ERROR = "validation_error"
    IO_ERROR = "io_error"


class IngestErrorDetails(BaseSchema):
    """Detailed ingest error context."""

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
    source_path: str | None = Field(None, description="Source file path")
    expected_fields: list[str] | None = Field(
        None, description="Expected field names for the record"
    )
    example: str | None = Field(None, description="Example input snippet for guidance")


class IngestErrorInfo(BaseSchema):
    """Structured ingest error data."""

    code: IngestErrorCode = Field(..., description="Ingest error code")
    message: str = Field(..., min_length=1, description="Error message")
    details: IngestErrorDetails | None = Field(None, description="Error details")

    def to_error_response(self) -> ErrorResponse:
        """Convert ingest error info to the standard error response schema.

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


class IngestError(Exception):
    """Ingest error with structured details."""

    def __init__(self, info: IngestErrorInfo) -> None:
        """Initialize the ingest error.

        Args:
            info: Structured ingest error information.
        """
        super().__init__(info.message)
        self.info = info


class IngestBatchError(Exception):
    """Ingest error containing multiple issues."""

    def __init__(self, errors: list[IngestErrorInfo]) -> None:
        """Initialize the batch ingest error.

        Args:
            errors: Collected ingest errors.
        """
        super().__init__(f"{len(errors)} ingest errors")
        self.errors = errors


@runtime_checkable
class IngestAdapterProtocol(Protocol):
    """Protocol for ingest adapters."""

    format: FileFormat

    async def load_source(self, source: IngestSource) -> list[SourceLine]:
        """Load a source file into SourceLine records.

        Raises:
            IngestError: For fatal ingest errors.
            IngestBatchError: For per-record validation issues.
        """
        raise NotImplementedError


def build_ingest_started_log(
    timestamp: Timestamp, run_id: RunId, source: IngestSource
) -> LogEntry:
    """Build a log entry for ingest start.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        source: Ingest source descriptor.

    Returns:
        LogEntry: Structured ingest log entry.
    """
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=IngestEvent.STARTED,
        run_id=run_id,
        phase=PhaseName.INGEST,
        message="Ingest started",
        data=IngestStartedData(
            source_path=source.input_path,
            format=_coerce_file_format(source.format),
        ).model_dump(exclude_none=True),
    )


def build_ingest_completed_log(
    timestamp: Timestamp,
    run_id: RunId,
    source: IngestSource,
    line_count: int,
) -> LogEntry:
    """Build a log entry for ingest completion.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        source: Ingest source descriptor.
        line_count: Number of source lines ingested.

    Returns:
        LogEntry: Structured ingest log entry.
    """
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=IngestEvent.COMPLETED,
        run_id=run_id,
        phase=PhaseName.INGEST,
        message="Ingest completed",
        data=IngestCompletedData(
            source_path=source.input_path,
            format=_coerce_file_format(source.format),
            line_count=line_count,
        ).model_dump(exclude_none=True),
    )


def build_ingest_failed_log(
    timestamp: Timestamp,
    run_id: RunId,
    source: IngestSource,
    error: IngestErrorInfo,
    error_count: int | None = None,
) -> LogEntry:
    """Build a log entry for ingest failure.

    Args:
        timestamp: ISO-8601 timestamp.
        run_id: Pipeline run identifier.
        source: Ingest source descriptor.
        error: Primary ingest error information.
        error_count: Optional total number of errors.

    Returns:
        LogEntry: Structured ingest log entry.
    """
    data = IngestFailedData(
        source_path=source.input_path,
        format=_coerce_file_format(source.format),
        error_code=str(error.code),
        error_message=error.message,
        error_count=error_count,
    ).model_dump(exclude_none=True)

    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.ERROR,
        event=IngestEvent.FAILED,
        run_id=run_id,
        phase=PhaseName.INGEST,
        message="Ingest failed",
        data=data,
    )


def _format_location(details: IngestErrorDetails | None) -> str | None:
    if details is None:
        return None
    if details.row_number is not None:
        return f"row {details.row_number}"
    if details.line_number is not None:
        return f"line {details.line_number}"
    return None


def _coerce_file_format(value: FileFormat | str) -> FileFormat:
    if isinstance(value, FileFormat):
        return value
    return FileFormat(value)
