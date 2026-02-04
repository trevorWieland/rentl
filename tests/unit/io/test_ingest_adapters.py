"""Unit tests for ingest adapters."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from rentl_core.ports.ingest import IngestBatchError, IngestErrorCode
from rentl_io.ingest import CsvIngestAdapter, JsonlIngestAdapter, TxtIngestAdapter
from rentl_schemas.io import IngestSource
from rentl_schemas.primitives import FileFormat


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_csv_ingest_parses_metadata_and_extra_columns(tmp_path: Path) -> None:
    """Parse CSV metadata and extra columns into metadata."""
    content = (
        "line_id,text,scene_id,speaker,metadata,emotion\n"
        'line_1,Hello,scene_1,Alice,"{""tone"":""calm""}",happy\n'
    )
    path = tmp_path / "source.csv"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.CSV)
    adapter = CsvIngestAdapter()
    lines = asyncio.run(adapter.load_source(source))

    assert len(lines) == 1
    assert lines[0].line_id == "line_1"
    assert lines[0].scene_id == "scene_1"
    assert lines[0].speaker == "Alice"
    assert lines[0].metadata == {"tone": "calm", "extra": {"emotion": "happy"}}
    assert lines[0].source_columns == [
        "line_id",
        "text",
        "scene_id",
        "speaker",
        "metadata",
        "emotion",
    ]


def test_csv_ingest_detects_missing_row_field(tmp_path: Path) -> None:
    """Raise ingest error when required CSV field is missing."""
    content = "line_id,text\n,Hello\n"
    path = tmp_path / "missing.csv"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.CSV)
    adapter = CsvIngestAdapter()

    with pytest.raises(IngestBatchError) as exc:
        asyncio.run(adapter.load_source(source))

    assert len(exc.value.errors) == 1
    assert exc.value.errors[0].code == IngestErrorCode.MISSING_FIELD
    assert exc.value.errors[0].details is not None
    assert exc.value.errors[0].details.row_number == 2


def test_csv_ingest_rejects_invalid_metadata(tmp_path: Path) -> None:
    """Raise parse error for invalid CSV metadata JSON."""
    content = "line_id,text,metadata\nline_1,Hello,{not-json}\n"
    path = tmp_path / "bad-meta.csv"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.CSV)
    adapter = CsvIngestAdapter()

    with pytest.raises(IngestBatchError) as exc:
        asyncio.run(adapter.load_source(source))

    assert len(exc.value.errors) == 1
    assert exc.value.errors[0].code == IngestErrorCode.PARSE_ERROR


def test_csv_ingest_rejects_metadata_conflict(tmp_path: Path) -> None:
    """Reject CSV metadata key conflicts with extra columns."""
    content = (
        "line_id,text,metadata,emotion\n"
        'line_1,Hello,"{""extra"":{""emotion"":""calm""}}",happy\n'
    )
    path = tmp_path / "conflict.csv"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.CSV)
    adapter = CsvIngestAdapter()

    with pytest.raises(IngestBatchError) as exc:
        asyncio.run(adapter.load_source(source))

    assert len(exc.value.errors) == 1
    assert exc.value.errors[0].code == IngestErrorCode.VALIDATION_ERROR


def test_jsonl_ingest_parses_lines(tmp_path: Path) -> None:
    """Parse JSONL lines into SourceLine records."""
    content = (
        '{"line_id":"line_1","text":"Hello"}\n'
        '{"line_id":"line_2","text":"Hi","metadata":{"note":"ok"}}\n'
    )
    path = tmp_path / "source.jsonl"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.JSONL)
    adapter = JsonlIngestAdapter()
    lines = asyncio.run(adapter.load_source(source))

    assert len(lines) == 2
    assert lines[1].metadata == {"note": "ok"}


def test_jsonl_ingest_rejects_invalid_json(tmp_path: Path) -> None:
    """Raise parse error when JSONL is invalid JSON."""
    content = "{not-json}\n"
    path = tmp_path / "bad.jsonl"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.JSONL)
    adapter = JsonlIngestAdapter()

    with pytest.raises(IngestBatchError) as exc:
        asyncio.run(adapter.load_source(source))

    assert len(exc.value.errors) == 1
    assert exc.value.errors[0].code == IngestErrorCode.PARSE_ERROR
    assert exc.value.errors[0].details is not None
    assert exc.value.errors[0].details.line_number == 1


def test_jsonl_ingest_rejects_non_object(tmp_path: Path) -> None:
    """Reject JSONL lines that are not objects."""
    content = "[]\n"
    path = tmp_path / "array.jsonl"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.JSONL)
    adapter = JsonlIngestAdapter()

    with pytest.raises(IngestBatchError) as exc:
        asyncio.run(adapter.load_source(source))

    assert len(exc.value.errors) == 1
    assert exc.value.errors[0].code == IngestErrorCode.VALIDATION_ERROR


def test_txt_ingest_builds_source_lines(tmp_path: Path) -> None:
    """Build SourceLine records from TXT lines."""
    content = "Hello\nWorld\n"
    path = tmp_path / "source.txt"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.TXT)
    adapter = TxtIngestAdapter()
    lines = asyncio.run(adapter.load_source(source))

    assert len(lines) == 2
    assert lines[0].line_id == "line_1"
    assert lines[0].metadata == {"source_line_index": 1}
    assert lines[1].line_id == "line_2"


def test_txt_ingest_rejects_empty_lines(tmp_path: Path) -> None:
    """Reject empty TXT lines as missing text."""
    content = "Hello\n\nWorld\n"
    path = tmp_path / "empty.txt"
    _write(path, content)

    source = IngestSource(input_path=str(path), format=FileFormat.TXT)
    adapter = TxtIngestAdapter()

    with pytest.raises(IngestBatchError) as exc:
        asyncio.run(adapter.load_source(source))

    assert len(exc.value.errors) == 1
    assert exc.value.errors[0].code == IngestErrorCode.MISSING_FIELD
    assert exc.value.errors[0].details is not None
    assert exc.value.errors[0].details.line_number == 2
