"""CLI entry point - thin adapter over rentl-core."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import typer
from pydantic import ValidationError
from rich import print as rprint

from rentl_core import VERSION
from rentl_core.ports.export import ExportBatchError, ExportError, ExportResult
from rentl_io import write_output
from rentl_schemas.io import ExportTarget, TranslatedLine
from rentl_schemas.primitives import FileFormat, UntranslatedPolicy
from rentl_schemas.responses import ApiResponse, ErrorResponse, MetaInfo

INPUT_OPTION = typer.Option(
    ..., "--input", "-i", help="JSONL file of TranslatedLine records"
)
OUTPUT_OPTION = typer.Option(
    ..., "--output", "-o", help="Path to write exported output"
)
FORMAT_OPTION = typer.Option(..., "--format", "-f", help="Output file format")
UNTRANSLATED_POLICY_OPTION = typer.Option(
    UntranslatedPolicy.ERROR,
    "--untranslated-policy",
    help="Policy for untranslated lines (error|warn|allow)",
)
INCLUDE_SOURCE_TEXT_OPTION = typer.Option(
    False, "--include-source-text", help="Include source_text column in CSV"
)
INCLUDE_SCENE_ID_OPTION = typer.Option(
    False, "--include-scene-id", help="Include scene_id column in CSV"
)
INCLUDE_SPEAKER_OPTION = typer.Option(
    False, "--include-speaker", help="Include speaker column in CSV"
)
COLUMN_ORDER_OPTION = typer.Option(
    None, "--column-order", help="Explicit CSV column order (repeatable)"
)
EXPECTED_LINE_COUNT_OPTION = typer.Option(
    None,
    "--expected-line-count",
    help="Optional expected line count for export audit",
)

app = typer.Typer(
    help="Agentic localization pipeline",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Rentl CLI."""


@app.command()
def version() -> None:
    """Display version information."""
    rprint(f"[bold]rentl[/bold] v{VERSION}")


@app.command()
def export(
    input_path: Path = INPUT_OPTION,
    output_path: Path = OUTPUT_OPTION,
    format: FileFormat = FORMAT_OPTION,
    untranslated_policy: UntranslatedPolicy = UNTRANSLATED_POLICY_OPTION,
    include_source_text: bool = INCLUDE_SOURCE_TEXT_OPTION,
    include_scene_id: bool = INCLUDE_SCENE_ID_OPTION,
    include_speaker: bool = INCLUDE_SPEAKER_OPTION,
    column_order: list[str] | None = COLUMN_ORDER_OPTION,
    expected_line_count: int | None = EXPECTED_LINE_COUNT_OPTION,
) -> None:
    """Export translated lines to CSV/JSONL/TXT."""
    try:
        lines = _load_translated_lines(input_path)
        target = ExportTarget(
            output_path=str(output_path),
            format=format,
            untranslated_policy=untranslated_policy,
            column_order=column_order,
            include_source_text=include_source_text,
            include_scene_id=include_scene_id,
            include_speaker=include_speaker,
            expected_line_count=expected_line_count,
        )
        result = asyncio.run(write_output(target, lines))
        response: ApiResponse[ExportResult] = ApiResponse(
            data=result, error=None, meta=MetaInfo(timestamp=_now_timestamp())
        )
    except ExportBatchError as exc:
        response = _batch_error_response(exc)
    except ExportError as exc:
        response = _error_response(exc.info.to_error_response())
    except ValueError as exc:
        response = _error_response(
            ErrorResponse(code="validation_error", message=str(exc), details=None)
        )

    print(response.model_dump_json())


def _now_timestamp() -> str:
    timestamp = datetime.now(UTC).isoformat()
    return timestamp.replace("+00:00", "Z")


def _load_translated_lines(path: Path) -> list[TranslatedLine]:
    lines: list[TranslatedLine] = []
    try:
        content = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Failed to read input: {exc}") from exc

    for line_number, raw_line in enumerate(content, start=1):
        if raw_line.strip() == "":
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"line {line_number}: JSONL line is not valid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise ValueError(f"line {line_number}: JSONL line must be an object")
        try:
            lines.append(TranslatedLine.model_validate(payload))
        except ValidationError as exc:
            raise ValueError(
                f"line {line_number}: JSONL line does not match TranslatedLine"
            ) from exc
    if not lines:
        raise ValueError("No translated lines found in input")
    return lines


def _error_response(error: ErrorResponse) -> ApiResponse[ExportResult]:
    return ApiResponse(
        data=None,
        error=error,
        meta=MetaInfo(timestamp=_now_timestamp()),
    )


def _batch_error_response(exc: ExportBatchError) -> ApiResponse[ExportResult]:
    error = exc.errors[0].to_error_response()
    if len(exc.errors) > 1:
        error = ErrorResponse(
            code=error.code,
            message=f"{len(exc.errors)} export errors; first: {error.message}",
            details=error.details,
        )
    return _error_response(error)


if __name__ == "__main__":
    app()
