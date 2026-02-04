"""Unit tests for event taxonomy schemas."""

from rentl_schemas.events import (
    ExportCompletedData,
    IngestCompletedData,
    PhaseEventData,
    RunCompletedData,
    RunStartedData,
)
from rentl_schemas.primitives import FileFormat, PhaseName, RunStatus


def test_run_started_data_dumps_phases() -> None:
    """RunStartedData serializes phase names."""
    data = RunStartedData(phases=[PhaseName.INGEST, PhaseName.EXPORT])
    payload = data.model_dump()
    assert payload["phases"] == [PhaseName.INGEST, PhaseName.EXPORT]


def test_run_completed_data_includes_status() -> None:
    """RunCompletedData includes final run status."""
    data = RunCompletedData(status=RunStatus.COMPLETED)
    payload = data.model_dump()
    assert payload["status"] == RunStatus.COMPLETED


def test_phase_event_data_serializes_phase() -> None:
    """PhaseEventData captures phase metadata."""
    data = PhaseEventData(
        phase=PhaseName.TRANSLATE,
        revision=2,
        target_language=None,
    )
    payload = data.model_dump(exclude_none=True)
    assert payload["phase"] == PhaseName.TRANSLATE
    assert payload["revision"] == 2


def test_ingest_completed_data_serializes_format() -> None:
    """IngestCompletedData stores file format and count."""
    data = IngestCompletedData(
        source_path="/tmp/input.csv",
        format=FileFormat.CSV,
        line_count=12,
    )
    payload = data.model_dump()
    assert payload["format"] == FileFormat.CSV
    assert payload["line_count"] == 12


def test_export_completed_data_optional_counts() -> None:
    """ExportCompletedData drops optional counts when missing."""
    data = ExportCompletedData(
        output_path="/tmp/output.jsonl",
        format=FileFormat.JSONL,
        line_count=3,
        untranslated_count=None,
        column_count=None,
    )
    payload = data.model_dump(exclude_none=True)
    assert payload["format"] == FileFormat.JSONL
    assert payload["line_count"] == 3
