"""Format router for export adapters."""

from __future__ import annotations

from rentl_core.ports.export import (
    ExportAdapterProtocol,
    ExportError,
    ExportErrorCode,
    ExportErrorDetails,
    ExportErrorInfo,
    ExportResult,
)
from rentl_io.export.csv_adapter import CsvExportAdapter
from rentl_io.export.jsonl_adapter import JsonlExportAdapter
from rentl_io.export.txt_adapter import TxtExportAdapter
from rentl_schemas.io import ExportTarget, TranslatedLine
from rentl_schemas.phases import EditPhaseOutput, TranslatePhaseOutput
from rentl_schemas.primitives import FileFormat

_ADAPTERS: dict[FileFormat, ExportAdapterProtocol] = {
    FileFormat.CSV: CsvExportAdapter(),
    FileFormat.JSONL: JsonlExportAdapter(),
    FileFormat.TXT: TxtExportAdapter(),
}


def get_export_adapter(file_format: FileFormat | str) -> ExportAdapterProtocol:
    """Return the export adapter for a given file format.

    Args:
        file_format: Requested file format.

    Returns:
        ExportAdapterProtocol: Adapter implementation for the format.

    Raises:
        ExportError: If the format is unsupported.
    """
    try:
        normalized_format = FileFormat(file_format)
    except ValueError as exc:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.INVALID_FORMAT,
                message="Unsupported export format",
                details=ExportErrorDetails(
                    field="format",
                    provided=str(file_format),
                    valid_options=[item.value for item in _ADAPTERS],
                ),
            )
        ) from exc

    adapter = _ADAPTERS.get(normalized_format)
    if adapter is None:
        raise ExportError(
            ExportErrorInfo(
                code=ExportErrorCode.INVALID_FORMAT,
                message="Unsupported export format",
                details=ExportErrorDetails(
                    field="format",
                    provided=normalized_format.value,
                    valid_options=[item.value for item in _ADAPTERS],
                ),
            )
        )
    return adapter


async def write_output(
    target: ExportTarget, lines: list[TranslatedLine]
) -> ExportResult:
    """Write translated lines to export target via the router.

    Args:
        target: Export target descriptor.
        lines: Translated lines to write.

    Returns:
        ExportResult: Export summary and warnings.
    """
    adapter = get_export_adapter(target.format)
    return await adapter.write_output(target, lines)


def select_export_lines(
    *,
    edit_output: EditPhaseOutput | None = None,
    translate_output: TranslatePhaseOutput | None = None,
) -> list[TranslatedLine]:
    """Select translated lines for export.

    Prefers edit output when available and falls back to translate output.

    Args:
        edit_output: Edit phase output payload.
        translate_output: Translate phase output payload.

    Returns:
        list[TranslatedLine]: Lines to export.

    Raises:
        ExportError: If no translated lines are available.
    """
    if edit_output is not None:
        return list(edit_output.edited_lines)
    if translate_output is not None:
        return list(translate_output.translated_lines)
    raise ExportError(
        ExportErrorInfo(
            code=ExportErrorCode.VALIDATION_ERROR,
            message="Export requires edited or translated lines",
            details=ExportErrorDetails(
                field="edited_lines",
                expected_fields=["edited_lines", "translated_lines"],
            ),
        )
    )


async def write_phase_output(
    target: ExportTarget,
    *,
    edit_output: EditPhaseOutput | None = None,
    translate_output: TranslatePhaseOutput | None = None,
) -> ExportResult:
    """Write translated lines from phase output via the router.

    Args:
        target: Export target descriptor.
        edit_output: Edit phase output payload.
        translate_output: Translate phase output payload.

    Returns:
        ExportResult: Export summary and warnings.
    """
    lines = select_export_lines(
        edit_output=edit_output, translate_output=translate_output
    )
    return await write_output(target, lines)
