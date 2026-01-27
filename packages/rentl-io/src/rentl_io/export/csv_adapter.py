"""CSV export adapter for TranslatedLine records."""

from __future__ import annotations

import asyncio
import csv
import json
from typing import cast

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
from rentl_schemas.primitives import FileFormat, JsonValue, UntranslatedPolicy

REQUIRED_COLUMNS = ("line_id", "text")
OPTIONAL_COLUMNS = ("scene_id", "speaker", "source_text", "metadata")
RESERVED_COLUMNS = set(REQUIRED_COLUMNS + OPTIONAL_COLUMNS)


class CsvExportAdapter:
    """CSV adapter implementation."""

    format = FileFormat.CSV

    async def write_output(
        self, target: ExportTarget, lines: list[TranslatedLine]
    ) -> ExportResult:
        """Write translated lines to CSV output.

        Args:
            target: Export target descriptor.
            lines: Translated lines to write.

        Returns:
            ExportResult: Export summary and warnings.
        """
        return await asyncio.to_thread(_write_csv_sync, target, lines)


def _write_csv_sync(target: ExportTarget, lines: list[TranslatedLine]) -> ExportResult:
    normalized_format = _normalize_format(target)
    if normalized_format != FileFormat.CSV:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.INVALID_FORMAT,
                message="CSV adapter received non-CSV target",
                details=ExportErrorDetails(
                    field="format",
                    provided=normalized_format.value,
                    valid_options=[FileFormat.CSV.value],
                    output_path=target.output_path,
                ),
            )
        )

    _validate_expected_line_count(target, lines)

    errors: list[ExportErrorInfo] = []
    prepared_rows, extra_columns = _prepare_rows(lines, target, errors)

    untranslated_warnings = _collect_untranslated_warnings(prepared_rows, target)
    if target.untranslated_policy == UntranslatedPolicy.ERROR:
        errors.extend(untranslated_warnings)

    if errors:
        raise ExportBatchError(errors)

    column_order = _resolve_column_order(
        target,
        lines,
        extra_columns,
        _has_base_metadata(prepared_rows),
    )
    warnings = _collect_column_warnings(
        lines, column_order, extra_columns, target, prepared_rows
    )
    if target.untranslated_policy == UntranslatedPolicy.WARN:
        warnings.extend(untranslated_warnings)

    rows = _build_rows(prepared_rows, column_order)

    try:
        with open(target.output_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=column_order)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    except OSError as exc:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.IO_ERROR,
                message=str(exc),
                details=ExportErrorDetails(output_path=target.output_path),
            )
        ) from exc

    untranslated_count = _count_untranslated(lines)
    summary = ExportSummary(
        output_path=target.output_path,
        format=normalized_format,
        line_count=len(lines),
        untranslated_count=untranslated_count,
        column_count=len(column_order),
        columns=column_order,
    )
    return ExportResult(summary=summary, warnings=warnings or None)


def _normalize_format(target: ExportTarget) -> FileFormat:
    try:
        return FileFormat(target.format)
    except ValueError as exc:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.INVALID_FORMAT,
                message="CSV adapter received invalid format",
                details=ExportErrorDetails(
                    field="format",
                    provided=str(target.format),
                    valid_options=[FileFormat.CSV.value],
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


def _prepare_rows(
    lines: list[TranslatedLine],
    target: ExportTarget,
    errors: list[ExportErrorInfo],
) -> tuple[
    list[tuple[TranslatedLine, dict[str, JsonValue] | None, dict[str, JsonValue], int]],
    list[str],
]:
    prepared: list[
        tuple[TranslatedLine, dict[str, JsonValue] | None, dict[str, JsonValue], int]
    ] = []
    extra_columns: set[str] = set()
    for index, line in enumerate(lines, start=1):
        row_number = index + 1
        try:
            base_metadata, extra = _split_metadata(
                line.metadata, row_number, target.output_path
            )
        except ExportError as exc:
            errors.append(exc.info)
            continue

        for key in extra:
            if key in RESERVED_COLUMNS:
                errors.append(
                    ExportErrorInfo(
                        code=ExportErrorCode.VALIDATION_ERROR,
                        message="CSV extra column conflicts with reserved column",
                        details=ExportErrorDetails(
                            field=key,
                            row_number=row_number,
                            output_path=target.output_path,
                        ),
                    )
                )
                continue
            extra_columns.add(key)

        prepared.append((line, base_metadata, extra, row_number))
    return prepared, sorted(extra_columns)


def _resolve_column_order(
    target: ExportTarget,
    lines: list[TranslatedLine],
    extra_columns: list[str],
    has_metadata: bool,
) -> list[str]:
    if target.column_order is not None:
        column_order = list(target.column_order)
    else:
        source_columns = _find_source_columns(lines)
        if source_columns is not None:
            column_order = source_columns
        else:
            column_order = [*REQUIRED_COLUMNS]
            if target.include_scene_id:
                column_order.append("scene_id")
            if target.include_speaker:
                column_order.append("speaker")
            if target.include_source_text:
                column_order.append("source_text")
            if has_metadata:
                column_order.append("metadata")
            column_order.extend(extra_columns)

    _validate_column_order(column_order, target)
    return column_order


def _find_source_columns(lines: list[TranslatedLine]) -> list[str] | None:
    for line in lines:
        if line.source_columns is None:
            continue
        if not line.source_columns:
            continue
        return list(line.source_columns)
    return None


def _validate_column_order(column_order: list[str], target: ExportTarget) -> None:
    if len(set(column_order)) != len(column_order):
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.VALIDATION_ERROR,
                message="CSV column_order contains duplicates",
                details=ExportErrorDetails(
                    field="column_order",
                    output_path=target.output_path,
                ),
            )
        )

    missing_required = [
        column for column in REQUIRED_COLUMNS if column not in column_order
    ]
    if missing_required:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.VALIDATION_ERROR,
                message="CSV column_order missing required columns",
                details=ExportErrorDetails(
                    field=", ".join(missing_required),
                    output_path=target.output_path,
                ),
            )
        )


def _collect_column_warnings(
    lines: list[TranslatedLine],
    column_order: list[str],
    extra_columns: list[str],
    target: ExportTarget,
    prepared_rows: list[
        tuple[TranslatedLine, dict[str, JsonValue] | None, dict[str, JsonValue], int]
    ],
) -> list[ExportErrorInfo]:
    warnings: list[ExportErrorInfo] = []
    missing_extra = [column for column in extra_columns if column not in column_order]
    if missing_extra:
        warnings.append(
            ExportErrorInfo(
                code=ExportErrorCode.DROPPED_COLUMN,
                message="CSV column_order excludes metadata extra columns",
                details=ExportErrorDetails(
                    field=", ".join(missing_extra),
                    output_path=target.output_path,
                ),
            )
        )

    if _has_base_metadata(prepared_rows) and "metadata" not in column_order:
        warnings.append(
            ExportErrorInfo(
                code=ExportErrorCode.DROPPED_COLUMN,
                message="CSV column_order excludes metadata column",
                details=ExportErrorDetails(
                    field="metadata",
                    output_path=target.output_path,
                ),
            )
        )

    if any(line.scene_id for line in lines) and "scene_id" not in column_order:
        warnings.append(
            ExportErrorInfo(
                code=ExportErrorCode.DROPPED_COLUMN,
                message="CSV column_order excludes scene_id column",
                details=ExportErrorDetails(
                    field="scene_id",
                    output_path=target.output_path,
                ),
            )
        )

    if any(line.speaker for line in lines) and "speaker" not in column_order:
        warnings.append(
            ExportErrorInfo(
                code=ExportErrorCode.DROPPED_COLUMN,
                message="CSV column_order excludes speaker column",
                details=ExportErrorDetails(
                    field="speaker",
                    output_path=target.output_path,
                ),
            )
        )

    if any(line.source_text for line in lines) and "source_text" not in column_order:
        warnings.append(
            ExportErrorInfo(
                code=ExportErrorCode.DROPPED_COLUMN,
                message="CSV column_order excludes source_text column",
                details=ExportErrorDetails(
                    field="source_text",
                    output_path=target.output_path,
                ),
            )
        )

    return warnings


def _build_rows(
    prepared_rows: list[
        tuple[TranslatedLine, dict[str, JsonValue] | None, dict[str, JsonValue], int]
    ],
    column_order: list[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line, base_metadata, extra, _row_number in prepared_rows:
        row: dict[str, str] = {}
        for column in column_order:
            if column == "line_id":
                row[column] = line.line_id
            elif column == "text":
                row[column] = line.text
            elif column == "scene_id":
                row[column] = line.scene_id or ""
            elif column == "speaker":
                row[column] = line.speaker or ""
            elif column == "source_text":
                row[column] = line.source_text or ""
            elif column == "metadata":
                row[column] = _format_metadata(base_metadata)
            else:
                row[column] = _format_csv_value(extra.get(column))
        rows.append(row)
    return rows


def _collect_untranslated_warnings(
    prepared_rows: list[
        tuple[TranslatedLine, dict[str, JsonValue] | None, dict[str, JsonValue], int]
    ],
    target: ExportTarget,
) -> list[ExportErrorInfo]:
    if target.untranslated_policy == UntranslatedPolicy.ALLOW:
        return []
    warnings: list[ExportErrorInfo] = []
    for line, _base_metadata, _extra, row_number in prepared_rows:
        if _is_untranslated(line):
            warnings.append(
                ExportErrorInfo(
                    code=ExportErrorCode.UNTRANSLATED_TEXT,
                    message="Translated text matches source text",
                    details=ExportErrorDetails(
                        field="text",
                        row_number=row_number,
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


def _has_base_metadata(
    prepared_rows: list[
        tuple[TranslatedLine, dict[str, JsonValue] | None, dict[str, JsonValue], int]
    ],
) -> bool:
    return any(
        base_metadata for _line, base_metadata, _extra, _row_number in prepared_rows
    )


def _split_metadata(
    metadata: dict[str, JsonValue] | None,
    row_number: int,
    output_path: str,
) -> tuple[dict[str, JsonValue] | None, dict[str, JsonValue]]:
    if metadata is None:
        return None, {}

    extra_value = metadata.get("extra")
    extra: dict[str, JsonValue]
    if extra_value is None:
        extra = {}
    elif isinstance(extra_value, dict):
        if not all(isinstance(key, str) for key in extra_value):
            raise ExportError(
                ExportErrorInfo(
                    code=ExportErrorCode.VALIDATION_ERROR,
                    message="CSV metadata.extra keys must be strings",
                    details=ExportErrorDetails(
                        field="metadata.extra",
                        row_number=row_number,
                        output_path=output_path,
                    ),
                )
            )
        extra = cast(dict[str, JsonValue], extra_value)
    else:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.VALIDATION_ERROR,
                message="CSV metadata.extra must be an object",
                details=ExportErrorDetails(
                    field="metadata.extra",
                    row_number=row_number,
                    output_path=output_path,
                ),
            )
        )

    base_metadata = {key: value for key, value in metadata.items() if key != "extra"}
    if not base_metadata:
        return None, extra
    return base_metadata, extra


def _format_metadata(metadata: dict[str, JsonValue] | None) -> str:
    if metadata is None:
        return ""
    if not metadata:
        return ""
    return json.dumps(metadata, ensure_ascii=False)


def _format_csv_value(value: JsonValue | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)
