"""Unit tests for export adapters."""

from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from uuid import UUID

import pytest

from rentl_core.ports.export import ExportBatchError, ExportError, ExportErrorCode
from rentl_io.export import (
    CsvExportAdapter,
    JsonlExportAdapter,
    TxtExportAdapter,
    get_export_adapter,
    select_export_lines,
)
from rentl_schemas.io import ExportTarget, TranslatedLine
from rentl_schemas.phases import EditPhaseOutput, TranslatePhaseOutput
from rentl_schemas.primitives import FileFormat, RunId, UntranslatedPolicy
from rentl_schemas.qa import LineEdit


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({key: value for key, value in row.items() if key is not None})
        return rows


RUN_ID: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")


def test_csv_export_expands_metadata_extra(tmp_path: Path) -> None:
    """CSV export expands metadata.extra into columns."""
    output = tmp_path / "output.csv"
    target = ExportTarget(
        output_path=str(output),
        format=FileFormat.CSV,
        include_source_text=True,
    )
    adapter = CsvExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            text="Hola",
            metadata={"tone": "calm", "extra": {"emotion": "happy", "stage": 1}},
        )
    ]

    result = asyncio.run(adapter.write_output(target, lines))
    assert result.warnings is None
    assert result.summary.column_count == 6

    with open(output, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            "line_id",
            "text",
            "source_text",
            "metadata",
            "emotion",
            "stage",
        ]

    rows = _read_csv(output)
    assert rows[0]["line_id"] == "line_1"
    assert rows[0]["text"] == "Hola"
    assert rows[0]["emotion"] == "happy"
    assert rows[0]["stage"] == "1"

    metadata = json.loads(rows[0]["metadata"])
    assert metadata == {"tone": "calm"}


def test_csv_export_rejects_untranslated_by_default(tmp_path: Path) -> None:
    """CSV export blocks untranslated text by default."""
    output = tmp_path / "blocked.csv"
    target = ExportTarget(output_path=str(output), format=FileFormat.CSV)
    adapter = CsvExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            source_text="Hello",  # Required for untranslated detection
            text="Hello",
            metadata=None,
        )
    ]

    with pytest.raises(ExportBatchError) as exc:
        asyncio.run(adapter.write_output(target, lines))

    assert len(exc.value.errors) == 1
    assert exc.value.errors[0].code == ExportErrorCode.UNTRANSLATED_TEXT
    assert exc.value.errors[0].details is not None
    assert exc.value.errors[0].details.row_number == 2


def test_csv_export_warns_on_untranslated(tmp_path: Path) -> None:
    """CSV export warns but continues for untranslated lines."""
    output = tmp_path / "warn.csv"
    target = ExportTarget(
        output_path=str(output),
        format=FileFormat.CSV,
        untranslated_policy=UntranslatedPolicy.WARN,
        include_source_text=True,
    )
    adapter = CsvExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            source_text="Hello",  # Required for untranslated detection
            text="Hello",
            metadata=None,
        )
    ]

    result = asyncio.run(adapter.write_output(target, lines))
    assert result.warnings is not None
    assert result.warnings[0].code == ExportErrorCode.UNTRANSLATED_TEXT
    assert output.exists()


def test_csv_export_allows_untranslated_with_policy(tmp_path: Path) -> None:
    """CSV export allows untranslated text with allow policy."""
    output = tmp_path / "allowed.csv"
    target = ExportTarget(
        output_path=str(output),
        format=FileFormat.CSV,
        untranslated_policy=UntranslatedPolicy.ALLOW,
        include_source_text=True,
    )
    adapter = CsvExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            text="Hello",
            metadata=None,
        )
    ]

    result = asyncio.run(adapter.write_output(target, lines))
    assert result.warnings is None
    rows = _read_csv(output)
    assert rows[0]["text"] == "Hello"


def test_csv_export_rejects_reserved_extra_columns(tmp_path: Path) -> None:
    """CSV export rejects metadata.extra keys that collide with reserved columns."""
    output = tmp_path / "conflict.csv"
    target = ExportTarget(output_path=str(output), format=FileFormat.CSV)
    adapter = CsvExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            text="Hola",
            metadata={"extra": {"text": "oops"}},
        )
    ]

    with pytest.raises(ExportBatchError) as exc:
        asyncio.run(adapter.write_output(target, lines))

    assert exc.value.errors[0].code == ExportErrorCode.VALIDATION_ERROR


def test_csv_export_column_order_controls_output(tmp_path: Path) -> None:
    """CSV export respects explicit column ordering."""
    output = tmp_path / "ordered.csv"
    target = ExportTarget(
        output_path=str(output),
        format=FileFormat.CSV,
        column_order=["line_id", "text"],
    )
    adapter = CsvExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            source_text="Hello",  # Provides a column to be dropped by column_order
            text="Hola",
            metadata=None,
        )
    ]

    result = asyncio.run(adapter.write_output(target, lines))
    assert result.warnings is not None
    assert result.warnings[0].code == ExportErrorCode.DROPPED_COLUMN

    with open(output, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["line_id", "text"]


def test_csv_export_uses_source_columns(tmp_path: Path) -> None:
    """CSV export uses source_columns when present."""
    output = tmp_path / "source-columns.csv"
    target = ExportTarget(output_path=str(output), format=FileFormat.CSV)
    adapter = CsvExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            text="Hola",
            metadata={"extra": {"emotion": "happy"}},
            source_columns=["line_id", "text", "source_text", "emotion"],
        )
    ]

    result = asyncio.run(adapter.write_output(target, lines))
    assert result.warnings is None

    with open(output, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            "line_id",
            "text",
            "source_text",
            "emotion",
        ]


def test_export_expected_line_count_mismatch(tmp_path: Path) -> None:
    """Export audit rejects mismatched line counts."""
    output = tmp_path / "count.jsonl"
    target = ExportTarget(
        output_path=str(output),
        format=FileFormat.JSONL,
        expected_line_count=2,
    )
    adapter = JsonlExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            text="Hola",
            metadata=None,
        )
    ]

    with pytest.raises(ExportError):
        asyncio.run(adapter.write_output(target, lines))


def test_jsonl_export_writes_lines(tmp_path: Path) -> None:
    """JSONL export writes one JSON object per line."""
    output = tmp_path / "output.jsonl"
    target = ExportTarget(output_path=str(output), format=FileFormat.JSONL)
    adapter = JsonlExportAdapter()

    lines = [
        TranslatedLine(
            line_id="line_1",
            text="Hola",
            metadata={"note": "ok"},
        )
    ]

    result = asyncio.run(adapter.write_output(target, lines))
    assert result.summary.line_count == 1
    contents = output.read_text(encoding="utf-8").strip().splitlines()
    payload = json.loads(contents[0])
    assert payload["line_id"] == "line_1"
    assert payload["text"] == "Hola"
    assert payload["metadata"] == {"note": "ok"}


def test_txt_export_writes_lines(tmp_path: Path) -> None:
    """TXT export writes one translation per line."""
    output = tmp_path / "output.txt"
    target = ExportTarget(output_path=str(output), format=FileFormat.TXT)
    adapter = TxtExportAdapter()

    lines = [TranslatedLine(line_id="line_1", text="Hola", metadata=None)]

    result = asyncio.run(adapter.write_output(target, lines))
    assert result.summary.line_count == 1
    assert output.read_text(encoding="utf-8") == "Hola\n"


def test_export_router_rejects_invalid_format() -> None:
    """Router rejects unsupported export format values."""
    with pytest.raises(ExportError):
        get_export_adapter("xml")


def test_select_export_lines_prefers_edit_output() -> None:
    """Export selection uses edit output when provided."""
    edit_output = EditPhaseOutput(
        run_id=RUN_ID,
        target_language="ja",
        edited_lines=[TranslatedLine(line_id="line_1", text="Hola")],
        change_log=[
            LineEdit(
                line_id="line_1",
                original_text="Hello",
                edited_text="Hola",
                reason="Tone update",
            )
        ],
    )
    translate_output = TranslatePhaseOutput(
        run_id=RUN_ID,
        target_language="ja",
        translated_lines=[TranslatedLine(line_id="line_1", text="Ciao")],
    )

    lines = select_export_lines(
        edit_output=edit_output, translate_output=translate_output
    )
    assert lines[0].text == "Hola"


def test_select_export_lines_falls_back_to_translate_output() -> None:
    """Export selection falls back to translate output."""
    translate_output = TranslatePhaseOutput(
        run_id=RUN_ID,
        target_language="ja",
        translated_lines=[TranslatedLine(line_id="line_1", text="Hola")],
    )

    lines = select_export_lines(translate_output=translate_output)
    assert lines[0].text == "Hola"
