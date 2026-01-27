"""JSONL export adapter for TranslatedLine records."""

from __future__ import annotations

import asyncio
import json

from rentl_core.ports.export import (
    ExportBatchError,
    ExportError,
    ExportErrorCode,
    ExportErrorDetails,
    ExportErrorInfo,
    ExportResult,
    ExportSummary,
)
from rentl_schemas.io import ExportTarget, TranslatedLine
from rentl_schemas.primitives import FileFormat, UntranslatedPolicy


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
    untranslated_warnings = _collect_untranslated_warnings(lines, target)
    if target.untranslated_policy == UntranslatedPolicy.ERROR and untranslated_warnings:
        raise ExportBatchError(untranslated_warnings)
    if target.untranslated_policy == UntranslatedPolicy.WARN:
        warnings.extend(untranslated_warnings)

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
        untranslated_count=_count_untranslated(lines),
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


def _collect_untranslated_warnings(
    lines: list[TranslatedLine],
    target: ExportTarget,
) -> list[ExportErrorInfo]:
    if target.untranslated_policy == UntranslatedPolicy.ALLOW:
        return []
    warnings: list[ExportErrorInfo] = []
    for line_number, line in enumerate(lines, start=1):
        if _is_untranslated(line):
            warnings.append(
                ExportErrorInfo(
                    code=ExportErrorCode.UNTRANSLATED_TEXT,
                    message="Translated text matches source text",
                    details=ExportErrorDetails(
                        field="text",
                        line_number=line_number,
                        output_path=target.output_path,
                    ),
                )
            )
    return warnings


def _count_untranslated(lines: list[TranslatedLine]) -> int:
    return sum(1 for line in lines if _is_untranslated(line))


def _is_untranslated(line: TranslatedLine) -> bool:
    if line.source_text is None:
        return False
    return line.text == line.source_text
