"""Unit tests for event taxonomy schemas."""

from uuid import UUID

from rentl_schemas.events import (
    ArtifactPersistedData,
    ArtifactPersistFailedData,
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
        column_count=None,
    )
    payload = data.model_dump(exclude_none=True)
    assert payload["format"] == FileFormat.JSONL
    assert payload["line_count"] == 3


def test_phase_event_data_coerces_phase_string() -> None:
    """Ensure PhaseEventData coerces phase string to PhaseName."""
    data = PhaseEventData(phase="translate")  # type: ignore[arg-type]
    assert data.phase == PhaseName.TRANSLATE


def test_artifact_persisted_data_coerces_phase_string() -> None:
    """Ensure ArtifactPersistedData coerces phase string to PhaseName."""
    data = ArtifactPersistedData(
        artifact_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0"),
        role="phase_output",
        phase="qa",  # type: ignore[arg-type]
        format="json",
    )
    assert data.phase == PhaseName.QA


def test_artifact_persist_failed_data_coerces_phase_string() -> None:
    """Ensure ArtifactPersistFailedData coerces phase string to PhaseName."""
    data = ArtifactPersistFailedData(
        artifact_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0"),
        role="phase_output",
        phase="edit",  # type: ignore[arg-type]
        format="json",
        error_message="disk full",
    )
    assert data.phase == PhaseName.EDIT
