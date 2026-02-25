"""Unit tests for pipeline schema PhaseName coercion."""

from uuid import UUID

from rentl_schemas.pipeline import (
    PhaseArtifacts,
    PhaseDependency,
    PhaseRevision,
    PhaseRunRecord,
    RunMetadata,
)
from rentl_schemas.primitives import PhaseName, PhaseStatus, RunStatus
from rentl_schemas.version import VersionInfo


def test_phase_dependency_coerces_phase_string() -> None:
    """Ensure PhaseDependency coerces phase string to PhaseName."""
    dep = PhaseDependency(phase="ingest", revision=1)  # type: ignore[arg-type]
    assert dep.phase == PhaseName.INGEST


def test_phase_revision_coerces_phase_string() -> None:
    """Ensure PhaseRevision coerces phase string to PhaseName."""
    rev = PhaseRevision(phase="context", revision=1)  # type: ignore[arg-type]
    assert rev.phase == PhaseName.CONTEXT


def test_phase_run_record_coerces_phase_string() -> None:
    """Ensure PhaseRunRecord coerces phase string to PhaseName."""
    record = PhaseRunRecord(
        phase_run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0"),
        phase="translate",  # type: ignore[arg-type]
        revision=1,
        status=PhaseStatus.COMPLETED,
    )
    assert record.phase == PhaseName.TRANSLATE


def test_phase_artifacts_coerces_phase_string() -> None:
    """Ensure PhaseArtifacts coerces phase string to PhaseName."""
    artifacts = PhaseArtifacts(phase="export", artifacts=[])  # type: ignore[arg-type]
    assert artifacts.phase == PhaseName.EXPORT


def test_run_metadata_coerces_current_phase_string() -> None:
    """Ensure RunMetadata coerces current_phase string to PhaseName."""
    metadata = RunMetadata(
        run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0"),
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        status=RunStatus.RUNNING,
        current_phase="qa",  # type: ignore[arg-type]
        created_at="2026-01-26T00:00:00Z",
    )
    assert metadata.current_phase == PhaseName.QA
