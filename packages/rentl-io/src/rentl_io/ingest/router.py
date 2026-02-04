"""Format router for ingest adapters."""

from __future__ import annotations

from rentl_core.ports.ingest import (
    IngestAdapterProtocol,
    IngestError,
    IngestErrorCode,
    IngestErrorDetails,
    IngestErrorInfo,
)
from rentl_io.ingest.csv_adapter import CsvIngestAdapter
from rentl_io.ingest.jsonl_adapter import JsonlIngestAdapter
from rentl_io.ingest.txt_adapter import TxtIngestAdapter
from rentl_schemas.io import IngestSource, SourceLine
from rentl_schemas.primitives import FileFormat

_ADAPTERS: dict[FileFormat, IngestAdapterProtocol] = {
    FileFormat.CSV: CsvIngestAdapter(),
    FileFormat.JSONL: JsonlIngestAdapter(),
    FileFormat.TXT: TxtIngestAdapter(),
}


def get_ingest_adapter(file_format: FileFormat | str) -> IngestAdapterProtocol:
    """Return the ingest adapter for a given file format.

    Args:
        file_format: Requested file format.

    Returns:
        IngestAdapterProtocol: Adapter implementation for the format.

    Raises:
        IngestError: If the format is unsupported.
    """
    try:
        normalized_format = FileFormat(file_format)
    except ValueError as exc:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.INVALID_FORMAT,
                message="Unsupported ingest format",
                details=IngestErrorDetails(
                    field="format",
                    provided=str(file_format),
                    valid_options=[item.value for item in _ADAPTERS],
                ),
            )
        ) from exc

    adapter = _ADAPTERS.get(normalized_format)
    if adapter is None:
        raise IngestError(
            IngestErrorInfo(
                code=IngestErrorCode.INVALID_FORMAT,
                message="Unsupported ingest format",
                details=IngestErrorDetails(
                    field="format",
                    provided=normalized_format.value,
                    valid_options=[item.value for item in _ADAPTERS],
                ),
            )
        )
    return adapter


async def load_source(source: IngestSource) -> list[SourceLine]:
    """Load a source file into SourceLine records via the router.

    Args:
        source: Ingest source descriptor.

    Returns:
        list[SourceLine]: Parsed source lines.
    """
    adapter = get_ingest_adapter(source.format)
    return await adapter.load_source(source)
