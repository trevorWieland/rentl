"""CSV ingest adapter for SourceLine records."""

from __future__ import annotations

import asyncio
import csv
import json
from typing import cast

from pydantic import ValidationError

from rentl_core.ports.ingest import (
    IngestBatchError,
    IngestError,
    IngestErrorCode,
    IngestErrorDetails,
    IngestErrorInfo,
)
from rentl_schemas.io import IngestSource, SourceLine
from rentl_schemas.primitives import FileFormat, JsonValue

REQUIRED_COLUMNS = ("line_id", "text")
OPTIONAL_COLUMNS = ("scene_id", "speaker", "metadata")
KNOWN_COLUMNS = set(REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
EXPECTED_FIELDS = [*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS]
CSV_HEADER_EXAMPLE = "line_id,text,scene_id,speaker,metadata"
CSV_ROW_EXAMPLE = 'line_1,Hello,scene_1,Alice,"{""tone"":""calm""}"'


class CsvIngestAdapter:
    """CSV adapter implementation."""

    format = FileFormat.CSV

    async def load_source(self, source: IngestSource) -> list[SourceLine]:
        """Load CSV content into SourceLine records.

        Args:
            source: Ingest source descriptor.

        Returns:
            list[SourceLine]: Parsed source lines.
        """
        return await asyncio.to_thread(_load_csv_sync, source)


def _load_csv_sync(source: IngestSource) -> list[SourceLine]:
    try:
        normalized_format = FileFormat(source.format)
    except ValueError as exc:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.INVALID_FORMAT,
                message="CSV adapter received invalid format",
                details=IngestErrorDetails(
                    field="format",
                    provided=str(source.format),
                    valid_options=[FileFormat.CSV.value],
                    source_path=source.input_path,
                ),
            )
        ) from exc

    if normalized_format != FileFormat.CSV:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.INVALID_FORMAT,
                message="CSV adapter received non-CSV source",
                details=IngestErrorDetails(
                    field="format",
                    provided=normalized_format.value,
                    valid_options=[FileFormat.CSV.value],
                    source_path=source.input_path,
                ),
            )
        )

    source_lines: list[SourceLine] = []
    errors: list[IngestErrorInfo] = []
    try:
        with open(source.input_path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise IngestError(
                    IngestErrorInfo(
                        code=IngestErrorCode.MISSING_FIELD,
                        message="CSV header row is missing",
                        details=IngestErrorDetails(
                            field="header",
                            source_path=source.input_path,
                            expected_fields=EXPECTED_FIELDS,
                            example=CSV_HEADER_EXAMPLE,
                        ),
                    )
                )

            missing = [
                name for name in REQUIRED_COLUMNS if name not in reader.fieldnames
            ]
            if missing:
                raise IngestError(
                    IngestErrorInfo(
                        code=IngestErrorCode.MISSING_FIELD,
                        message="CSV is missing required columns",
                        details=IngestErrorDetails(
                            field=", ".join(missing),
                            valid_options=list(REQUIRED_COLUMNS),
                            source_path=source.input_path,
                            expected_fields=EXPECTED_FIELDS,
                            example=CSV_HEADER_EXAMPLE,
                        ),
                    )
                )

            source_columns = list(reader.fieldnames)
            row_number = 2
            for row in reader:
                try:
                    line_id_value = row.get("line_id")
                    text_value = row.get("text")
                    if line_id_value is None or line_id_value == "":
                        raise IngestError(
                            IngestErrorInfo(
                                code=IngestErrorCode.MISSING_FIELD,
                                message="CSV row missing line_id",
                                details=IngestErrorDetails(
                                    field="line_id",
                                    row_number=row_number,
                                    source_path=source.input_path,
                                    expected_fields=EXPECTED_FIELDS,
                                    example=CSV_ROW_EXAMPLE,
                                ),
                            )
                        )
                    if text_value is None or text_value == "":
                        raise IngestError(
                            IngestErrorInfo(
                                code=IngestErrorCode.MISSING_FIELD,
                                message="CSV row missing text",
                                details=IngestErrorDetails(
                                    field="text",
                                    row_number=row_number,
                                    source_path=source.input_path,
                                    expected_fields=EXPECTED_FIELDS,
                                    example=CSV_ROW_EXAMPLE,
                                ),
                            )
                        )

                    scene_id_value = _optional_str(row.get("scene_id"))
                    speaker_value = _optional_str(row.get("speaker"))
                    metadata_value = _optional_str(row.get("metadata"))

                    metadata = _parse_metadata(
                        metadata_value, row_number, source.input_path
                    )
                    extra_metadata = _extract_extra_metadata(row)
                    metadata = _merge_metadata(
                        metadata, extra_metadata, row_number, source.input_path
                    )

                    source_line = SourceLine(
                        line_id=line_id_value,
                        scene_id=scene_id_value,
                        speaker=speaker_value,
                        text=text_value,
                        metadata=metadata,
                        source_columns=source_columns,
                    )
                except IngestError as exc:
                    errors.append(exc.info)
                except ValidationError as exc:
                    errors.append(
                        IngestErrorInfo(
                            code=IngestErrorCode.VALIDATION_ERROR,
                            message=str(exc),
                            details=IngestErrorDetails(
                                row_number=row_number,
                                source_path=source.input_path,
                            ),
                        )
                    )
                else:
                    source_lines.append(source_line)
                finally:
                    row_number += 1
    except IngestError:
        raise
    except OSError as exc:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.IO_ERROR,
                message=str(exc),
                details=IngestErrorDetails(source_path=source.input_path),
            )
        ) from exc

    if errors:
        raise IngestBatchError(errors)

    return source_lines


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    if value == "":
        return None
    return value


def _parse_metadata(
    value: str | None, row_number: int, source_path: str
) -> dict[str, JsonValue] | None:
    if value is None:
        return None
    try:
        parsed: object = json.loads(value)
    except json.JSONDecodeError as exc:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.PARSE_ERROR,
                message="CSV metadata is not valid JSON",
                details=IngestErrorDetails(
                    field="metadata",
                    row_number=row_number,
                    column_name="metadata",
                    provided=value,
                    source_path=source_path,
                ),
            )
        ) from exc

    if not isinstance(parsed, dict):
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.VALIDATION_ERROR,
                message="CSV metadata must be a JSON object",
                details=IngestErrorDetails(
                    field="metadata",
                    row_number=row_number,
                    column_name="metadata",
                    source_path=source_path,
                ),
            )
        )

    return cast(dict[str, JsonValue], parsed)


def _extract_extra_metadata(
    row: dict[str, str | None],
) -> dict[str, JsonValue]:
    extra: dict[str, JsonValue] = {}
    for key, value in row.items():
        if key in KNOWN_COLUMNS:
            continue
        if key is None:
            continue
        cleaned = _optional_str(value)
        if cleaned is None:
            continue
        extra[key] = cleaned
    return extra


def _merge_metadata(
    base: dict[str, JsonValue] | None,
    extra: dict[str, JsonValue],
    row_number: int,
    source_path: str,
) -> dict[str, JsonValue] | None:
    if base is None and not extra:
        return None

    merged: dict[str, JsonValue] = {}
    if base is not None:
        merged.update(base)
    if not extra:
        return merged

    extra_container = merged.get("extra")
    if extra_container is None:
        merged["extra"] = extra
        return merged
    if not isinstance(extra_container, dict):
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.VALIDATION_ERROR,
                message="CSV metadata extra must be a JSON object",
                details=IngestErrorDetails(
                    field="metadata.extra",
                    row_number=row_number,
                    column_name="metadata",
                    source_path=source_path,
                ),
            )
        )

    for key, value in extra.items():
        if key in extra_container:
            raise IngestError(
                IngestErrorInfo(
                    code=IngestErrorCode.VALIDATION_ERROR,
                    message="CSV metadata extra key conflicts with column name",
                    details=IngestErrorDetails(
                        field=key,
                        row_number=row_number,
                        column_name=key,
                        source_path=source_path,
                    ),
                )
            )
        extra_container[key] = value

    merged["extra"] = extra_container
    return merged
