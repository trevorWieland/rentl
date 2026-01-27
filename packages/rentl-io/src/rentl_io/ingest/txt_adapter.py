"""TXT ingest adapter for SourceLine records."""

from __future__ import annotations

import asyncio

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


class TxtIngestAdapter:
    """TXT adapter implementation."""

    format = FileFormat.TXT

    async def load_source(self, source: IngestSource) -> list[SourceLine]:
        """Load TXT content into SourceLine records.

        Args:
            source: Ingest source descriptor.

        Returns:
            list[SourceLine]: Parsed source lines.
        """
        return await asyncio.to_thread(_load_txt_sync, source)


def _load_txt_sync(source: IngestSource) -> list[SourceLine]:
    try:
        normalized_format = FileFormat(source.format)
    except ValueError as exc:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.INVALID_FORMAT,
                message="TXT adapter received invalid format",
                details=IngestErrorDetails(
                    field="format",
                    provided=str(source.format),
                    valid_options=[FileFormat.TXT.value],
                    source_path=source.input_path,
                ),
            )
        ) from exc

    if normalized_format != FileFormat.TXT:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.INVALID_FORMAT,
                message="TXT adapter received non-TXT source",
                details=IngestErrorDetails(
                    field="format",
                    provided=normalized_format.value,
                    valid_options=[FileFormat.TXT.value],
                    source_path=source.input_path,
                ),
            )
        )

    source_lines: list[SourceLine] = []
    errors: list[IngestErrorInfo] = []
    try:
        with open(source.input_path, encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                text_value = _strip_line_ending(raw_line)
                if text_value == "":
                    errors.append(
                        IngestErrorInfo(
                            code=IngestErrorCode.MISSING_FIELD,
                            message="TXT line is empty",
                            details=IngestErrorDetails(
                                field="text",
                                line_number=line_number,
                                source_path=source.input_path,
                            ),
                        )
                    )
                    continue

                line_id_value = f"line_{line_number}"
                metadata: dict[str, JsonValue] = {"source_line_index": line_number}
                try:
                    source_line = SourceLine(
                        line_id=line_id_value,
                        scene_id=None,
                        speaker=None,
                        text=text_value,
                        metadata=metadata,
                    )
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


def _strip_line_ending(value: str) -> str:
    value = value.removesuffix("\n")
    value = value.removesuffix("\r")
    return value
