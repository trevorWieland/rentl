"""JSONL ingest adapter for SourceLine records."""

from __future__ import annotations

import asyncio
import json

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

ALLOWED_KEYS = {"line_id", "scene_id", "speaker", "text", "metadata"}
EXPECTED_FIELDS = ["line_id", "text", "scene_id", "speaker", "metadata"]
JSONL_EXAMPLE = (
    '{"line_id":"line_1","text":"Hello","scene_id":"scene_1",'
    '"speaker":"Alice","metadata":{"tone":"calm"}}'
)


class JsonlIngestAdapter:
    """JSONL adapter implementation."""

    format = FileFormat.JSONL

    async def load_source(self, source: IngestSource) -> list[SourceLine]:
        """Load JSONL content into SourceLine records.

        Args:
            source: Ingest source descriptor.

        Returns:
            list[SourceLine]: Parsed source lines.
        """
        return await asyncio.to_thread(_load_jsonl_sync, source)


def _load_jsonl_sync(source: IngestSource) -> list[SourceLine]:
    try:
        normalized_format = FileFormat(source.format)
    except ValueError as exc:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.INVALID_FORMAT,
                message="JSONL adapter received invalid format",
                details=IngestErrorDetails(
                    field="format",
                    provided=str(source.format),
                    valid_options=[FileFormat.JSONL.value],
                    source_path=source.input_path,
                ),
            )
        ) from exc

    if normalized_format != FileFormat.JSONL:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.INVALID_FORMAT,
                message="JSONL adapter received non-JSONL source",
                details=IngestErrorDetails(
                    field="format",
                    provided=normalized_format.value,
                    valid_options=[FileFormat.JSONL.value],
                    source_path=source.input_path,
                ),
            )
        )

    source_lines: list[SourceLine] = []
    errors: list[IngestErrorInfo] = []
    try:
        with open(source.input_path, encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if raw_line.strip() == "":
                    continue
                try:
                    parsed: object = json.loads(raw_line)
                except json.JSONDecodeError:
                    errors.append(
                        IngestErrorInfo(
                            code=IngestErrorCode.PARSE_ERROR,
                            message="JSONL line is not valid JSON",
                            details=IngestErrorDetails(
                                line_number=line_number,
                                source_path=source.input_path,
                                expected_fields=EXPECTED_FIELDS,
                                example=JSONL_EXAMPLE,
                            ),
                        )
                    )
                    continue

                if not isinstance(parsed, dict):
                    errors.append(
                        IngestErrorInfo(
                            code=IngestErrorCode.VALIDATION_ERROR,
                            message="JSONL line must be a JSON object",
                            details=IngestErrorDetails(
                                line_number=line_number,
                                source_path=source.input_path,
                                expected_fields=EXPECTED_FIELDS,
                                example=JSONL_EXAMPLE,
                            ),
                        )
                    )
                    continue

                if not all(isinstance(key, str) for key in parsed):
                    errors.append(
                        IngestErrorInfo(
                            code=IngestErrorCode.VALIDATION_ERROR,
                            message="JSONL object keys must be strings",
                            details=IngestErrorDetails(
                                line_number=line_number,
                                source_path=source.input_path,
                                expected_fields=EXPECTED_FIELDS,
                                example=JSONL_EXAMPLE,
                            ),
                        )
                    )
                    continue

                json_obj: dict[str, object] = {
                    key: value for key, value in parsed.items() if isinstance(key, str)
                }
                unknown_keys = [key for key in json_obj if key not in ALLOWED_KEYS]
                if unknown_keys:
                    errors.append(
                        IngestErrorInfo(
                            code=IngestErrorCode.VALIDATION_ERROR,
                            message="JSONL object has unexpected fields",
                            details=IngestErrorDetails(
                                field=", ".join(unknown_keys),
                                line_number=line_number,
                                source_path=source.input_path,
                                expected_fields=EXPECTED_FIELDS,
                                example=JSONL_EXAMPLE,
                            ),
                        )
                    )
                    continue

                try:
                    line_id_value = _require_str(
                        json_obj, "line_id", line_number, source.input_path
                    )
                    text_value = _require_str(
                        json_obj, "text", line_number, source.input_path
                    )
                    scene_id_value = _optional_str_value(
                        json_obj.get("scene_id"),
                        "scene_id",
                        line_number,
                        source.input_path,
                    )
                    speaker_value = _optional_str_value(
                        json_obj.get("speaker"),
                        "speaker",
                        line_number,
                        source.input_path,
                    )
                    metadata_value = _optional_metadata(
                        json_obj, line_number, source.input_path
                    )

                    source_line = SourceLine(
                        line_id=line_id_value,
                        scene_id=scene_id_value,
                        speaker=speaker_value,
                        text=text_value,
                        metadata=metadata_value,
                    )
                except IngestError as exc:
                    errors.append(exc.info)
                except ValidationError as exc:
                    errors.append(
                        IngestErrorInfo(
                            code=IngestErrorCode.VALIDATION_ERROR,
                            message=str(exc),
                            details=IngestErrorDetails(
                                line_number=line_number,
                                source_path=source.input_path,
                            ),
                        )
                    )
                else:
                    source_lines.append(source_line)
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


def _require_str(
    payload: dict[str, object],
    field: str,
    line_number: int,
    source_path: str,
) -> str:
    value = payload.get(field)
    if value is None:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.MISSING_FIELD,
                message="JSONL object missing required field",
                details=IngestErrorDetails(
                    field=field,
                    line_number=line_number,
                    source_path=source_path,
                    expected_fields=EXPECTED_FIELDS,
                    example=JSONL_EXAMPLE,
                ),
            )
        )
    if not isinstance(value, str):
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.VALIDATION_ERROR,
                message="JSONL field must be a string",
                details=IngestErrorDetails(
                    field=field,
                    line_number=line_number,
                    source_path=source_path,
                    expected_fields=EXPECTED_FIELDS,
                    example=JSONL_EXAMPLE,
                ),
            )
        )
    return value


def _optional_str_value(
    value: object,
    field: str,
    line_number: int,
    source_path: str,
) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise IngestError(
        IngestErrorInfo(
            code=IngestErrorCode.VALIDATION_ERROR,
            message="JSONL field must be a string",
            details=IngestErrorDetails(
                field=field,
                line_number=line_number,
                source_path=source_path,
                expected_fields=EXPECTED_FIELDS,
                example=JSONL_EXAMPLE,
            ),
        )
    )


def _optional_metadata(
    payload: dict[str, object],
    line_number: int,
    source_path: str,
) -> dict[str, JsonValue] | None:
    if "metadata" not in payload:
        return None
    value = payload.get("metadata")
    if value is None:
        return None
    return _require_json_object(value, line_number, source_path)


def _require_json_object(
    value: object, line_number: int, source_path: str
) -> dict[str, JsonValue]:
    json_value = _as_json_value(value, line_number, source_path)
    if not isinstance(json_value, dict):
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.VALIDATION_ERROR,
                message="JSONL metadata must be a JSON object",
                details=IngestErrorDetails(
                    field="metadata", line_number=line_number, source_path=source_path
                ),
            )
        )
    return json_value


def _as_json_value(value: object, line_number: int, source_path: str) -> JsonValue:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_as_json_value(item, line_number, source_path) for item in value]
    if isinstance(value, dict):
        converted: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise IngestError(
                    IngestErrorInfo(
                        code=IngestErrorCode.VALIDATION_ERROR,
                        message="JSONL metadata keys must be strings",
                        details=IngestErrorDetails(
                            field="metadata",
                            line_number=line_number,
                            source_path=source_path,
                        ),
                    )
                )
            converted[key] = _as_json_value(item, line_number, source_path)
        return converted
    raise IngestError(
        IngestErrorInfo(
            code=IngestErrorCode.VALIDATION_ERROR,
            message="JSONL value is not JSON-serializable",
            details=IngestErrorDetails(
                line_number=line_number, source_path=source_path
            ),
        )
    )
