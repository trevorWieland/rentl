"""Unit tests for storage schema validation."""

from uuid import UUID

import pytest

from rentl_schemas.pipeline import PhaseRevision, RunMetadata, RunState
from rentl_schemas.primitives import (
    PhaseName,
    PhaseStatus,
    RunId,
    RunStatus,
)
from rentl_schemas.progress import (
    PhaseProgress,
    ProgressPercentMode,
    ProgressSummary,
    RunProgress,
)
from rentl_schemas.storage import (
    ArtifactFormat,
    ArtifactMetadata,
    ArtifactRole,
    RunIndexRecord,
    RunStateRecord,
    StorageReference,
)
from rentl_schemas.version import VersionInfo


def _build_run_state(run_id: RunId) -> RunState:
    metadata = RunMetadata(
        run_id=run_id,
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        status=RunStatus.PENDING,
        current_phase=None,
        created_at="2026-01-26T00:00:00Z",
        started_at=None,
        completed_at=None,
    )
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    progress = RunProgress(
        phases=[
            PhaseProgress(
                phase=PhaseName.INGEST,
                status=PhaseStatus.PENDING,
                summary=summary,
                metrics=None,
                started_at=None,
                completed_at=None,
            )
        ],
        summary=summary,
        phase_weights=None,
    )
    return RunState(
        metadata=metadata,
        progress=progress,
        artifacts=[],
        phase_history=None,
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )


def test_storage_reference_requires_path_or_uri() -> None:
    """StorageReference requires a path or URI."""
    with pytest.raises(ValueError):
        StorageReference(backend=None, path=None, uri=None)


def test_artifact_metadata_accepts_location() -> None:
    """Artifact metadata accepts a valid storage location."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")
    metadata = ArtifactMetadata(
        artifact_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b1"),
        run_id=run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.CONTEXT,
        target_language=None,
        format=ArtifactFormat.JSONL,
        created_at="2026-01-26T00:00:00Z",
        location=StorageReference(backend=None, path="/tmp/artifact.jsonl", uri=None),
        description=None,
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )
    payload = metadata.model_dump()
    assert payload["location"]["path"] == "/tmp/artifact.jsonl"


def test_run_state_record_round_trip() -> None:
    """RunStateRecord serializes with required fields."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b2")
    state = _build_run_state(run_id)
    record = RunStateRecord(
        run_id=run_id,
        stored_at="2026-01-26T00:00:01Z",
        state=state,
        location=None,
        checksum_sha256=None,
    )
    payload = record.model_dump()
    assert payload["state"]["metadata"]["run_id"] == run_id


def test_run_index_record_requires_targets() -> None:
    """RunIndexRecord requires at least one target language."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b3")
    metadata = RunMetadata(
        run_id=run_id,
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        status=RunStatus.PENDING,
        current_phase=None,
        created_at="2026-01-26T00:00:00Z",
        started_at=None,
        completed_at=None,
    )
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    with pytest.raises(ValueError):
        RunIndexRecord(
            metadata=metadata,
            project_name="demo",
            source_language="en",
            target_languages=[],
            updated_at="2026-01-26T00:00:02Z",
            progress=summary,
            last_error=None,
        )


def test_run_state_revisions_require_unique_pairs() -> None:
    """RunState requires unique phase/target pairs for revisions."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b4")
    metadata = RunMetadata(
        run_id=run_id,
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        status=RunStatus.PENDING,
        current_phase=None,
        created_at="2026-01-26T00:00:00Z",
        started_at=None,
        completed_at=None,
    )
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    progress = RunProgress(
        phases=[
            PhaseProgress(
                phase=PhaseName.INGEST,
                status=PhaseStatus.PENDING,
                summary=summary,
                metrics=None,
                started_at=None,
                completed_at=None,
            )
        ],
        summary=summary,
        phase_weights=None,
    )
    with pytest.raises(ValueError):
        RunState(
            metadata=metadata,
            progress=progress,
            artifacts=[],
            phase_history=None,
            phase_revisions=[
                PhaseRevision(
                    phase=PhaseName.CONTEXT,
                    target_language=None,
                    revision=1,
                ),
                PhaseRevision(
                    phase=PhaseName.CONTEXT,
                    target_language=None,
                    revision=2,
                ),
            ],
            last_error=None,
            qa_summary=None,
        )
