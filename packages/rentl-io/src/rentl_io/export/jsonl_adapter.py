"""JSONL export adapter for TranslatedLine records."""

from __future__ import annotations

import asyncio
import json

from rentl_core.ports.export import (
    ExportError,
    ExportErrorCode,
    ExportErrorDetails,
    ExportErrorInfo,
    ExportResult,
    ExportSummary,
)
from rentl_schemas.io import ExportTarget, TranslatedLine
from rentl_schemas.primitives import FileFormat


class JsonlExportAdapter:
    """JSONL adapter implementation."""

    format = FileFormat.JSONL

    async def write_output(
        self, target: ExportTarget, lines: list[TranslatedLine]
    ) -> ExportResult:
        """Write translated lines to JSONL output.

        Args:
            target: Export target descriptor.
            lines: Translated lines to write.

        Returns:
            ExportResult: Export summary and warnings.
        """
        return await asyncio.to_thread(_write_jsonl_sync, target, lines)


def _write_jsonl_sync(
    target: ExportTarget, lines: list[TranslatedLine]
) -> ExportResult:
    normalized_format = _normalize_format(target)
    if normalized_format != FileFormat.JSONL:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.INVALID_FORMAT,
                message="JSONL adapter received non-JSONL target",
                details=ExportErrorDetails(
                    field="format",
                    provided=normalized_format.value,
                    valid_options=[FileFormat.JSONL.value],
                    output_path=target.output_path,
                ),
            )
        )

    _validate_expected_line_count(target, lines)

    warnings: list[ExportErrorInfo] = []

    try:
        with open(target.output_path, "w", encoding="utf-8") as handle:
            for line in lines:
                payload = line.model_dump(exclude_none=True)
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.IO_ERROR,
                message=str(exc),
                details=ExportErrorDetails(output_path=target.output_path),
            )
        ) from exc

    summary = ExportSummary(
        output_path=target.output_path,
        format=normalized_format,
        line_count=len(lines),
        column_count=None,
        columns=None,
    )
    return ExportResult(summary=summary, warnings=warnings or None)


def _normalize_format(target: ExportTarget) -> FileFormat:
    try:
        return FileFormat(target.format)
    except ValueError as exc:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.INVALID_FORMAT,
                message="JSONL adapter received invalid format",
                details=ExportErrorDetails(
                    field="format",
                    provided=str(target.format),
                    valid_options=[FileFormat.JSONL.value],
                    output_path=target.output_path,
                ),
            )
        ) from exc


def _validate_expected_line_count(
    target: ExportTarget, lines: list[TranslatedLine]
) -> None:
    if target.expected_line_count is None:
        return
    if len(lines) == target.expected_line_count:
        return
    raise ExportError(
        ExportErrorInfo(
            code=ExportErrorCode.VALIDATION_ERROR,
            message="Export line count does not match expected value",
            details=ExportErrorDetails(
                field="expected_line_count",
                provided=str(len(lines)),
                output_path=target.output_path,
            ),
        )
    )
