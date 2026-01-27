"""Unit tests for filesystem storage adapters."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import Field

from rentl_core.ports.storage import StorageError, StorageErrorCode
from rentl_io.storage import (
    FileSystemArtifactStore,
    FileSystemLogStore,
    FileSystemRunStateStore,
)
from rentl_schemas.base import BaseSchema
from rentl_schemas.logs import LogEntry
from rentl_schemas.pipeline import RunMetadata, RunState
from rentl_schemas.primitives import (
    ArtifactId,
    LogLevel,
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


class _ArtifactPayload(BaseSchema):
    """Payload schema for artifact tests."""

    value: str = Field(..., min_length=1, description="Payload value")


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
        last_error=None,
        qa_summary=None,
    )


def test_filesystem_run_state_store_round_trip(tmp_path: Path) -> None:
    """Run state store writes and loads snapshots."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb600")
    store = FileSystemRunStateStore(base_dir=str(tmp_path / "state"))
    record = RunStateRecord(
        run_id=run_id,
        stored_at="2026-01-26T00:00:01Z",
        state=_build_run_state(run_id),
        location=None,
        checksum_sha256=None,
    )

    asyncio.run(store.save_run_state(record))
    loaded = asyncio.run(store.load_run_state(run_id))
    assert loaded is not None
    assert loaded.state.metadata.run_id == run_id

    index_record = RunIndexRecord(
        metadata=record.state.metadata,
        project_name="demo",
        source_language="en",
        target_languages=["ja"],
        updated_at="2026-01-26T00:00:02Z",
        progress=record.state.progress.summary,
        last_error=None,
    )
    asyncio.run(store.save_run_index(index_record))
    records = asyncio.run(store.list_run_index())
    assert records[0].metadata.run_id == run_id


def test_filesystem_artifact_store_json_round_trip(tmp_path: Path) -> None:
    """Artifact store writes JSON artifacts and reloads them."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb601")
    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb602")
    store = FileSystemArtifactStore(base_dir=str(tmp_path / "artifacts"))
    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        run_id=run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.CONTEXT,
        target_language=None,
        format=ArtifactFormat.JSON,
        created_at="2026-01-26T00:00:03Z",
        location=StorageReference(backend=None, path="/tmp/placeholder.json", uri=None),
        description=None,
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )
    payload = _ArtifactPayload(value="hello")

    stored = asyncio.run(store.write_artifact_json(metadata, payload))
    assert stored.location.path is not None

    loaded = asyncio.run(store.load_artifact_json(artifact_id, _ArtifactPayload))
    assert loaded.value == "hello"

    artifacts = asyncio.run(store.list_artifacts(run_id))
    assert artifacts


def test_filesystem_artifact_store_rejects_unsupported_format(
    tmp_path: Path,
) -> None:
    """Artifact store rejects mismatched formats."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb606")
    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb607")
    store = FileSystemArtifactStore(base_dir=str(tmp_path / "artifacts"))
    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        run_id=run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.CONTEXT,
        target_language=None,
        format=ArtifactFormat.JSONL,
        created_at="2026-01-26T00:00:06Z",
        location=StorageReference(
            backend=None, path="/tmp/placeholder.jsonl", uri=None
        ),
        description=None,
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )
    payload = _ArtifactPayload(value="hello")

    with pytest.raises(StorageError) as exc_info:
        asyncio.run(store.write_artifact_json(metadata, payload))
    assert exc_info.value.info.code == StorageErrorCode.UNSUPPORTED_FORMAT


def test_filesystem_artifact_store_jsonl_round_trip(tmp_path: Path) -> None:
    """Artifact store writes JSONL artifacts and reloads them."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb603")
    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb604")
    store = FileSystemArtifactStore(base_dir=str(tmp_path / "artifacts"))
    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        run_id=run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.TRANSLATE,
        target_language="ja",
        format=ArtifactFormat.JSONL,
        created_at="2026-01-26T00:00:04Z",
        location=StorageReference(
            backend=None, path="/tmp/placeholder.jsonl", uri=None
        ),
        description=None,
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )
    payloads = [_ArtifactPayload(value="one"), _ArtifactPayload(value="two")]

    stored = asyncio.run(store.write_artifact_jsonl(metadata, payloads))
    assert stored.location.path is not None

    loaded = asyncio.run(store.load_artifact_jsonl(artifact_id, _ArtifactPayload))
    assert [item.value for item in loaded] == ["one", "two"]


def test_filesystem_artifact_store_missing_artifact(tmp_path: Path) -> None:
    """Artifact store returns not found for missing artifacts."""
    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb608")
    store = FileSystemArtifactStore(base_dir=str(tmp_path / "artifacts"))

    with pytest.raises(StorageError) as exc_info:
        asyncio.run(store.load_artifact_json(artifact_id, _ArtifactPayload))
    assert exc_info.value.info.code == StorageErrorCode.NOT_FOUND


def test_filesystem_artifact_store_invalid_json(tmp_path: Path) -> None:
    """Artifact store surfaces serialization errors on invalid JSON."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb609")
    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb610")
    store = FileSystemArtifactStore(base_dir=str(tmp_path / "artifacts"))
    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        run_id=run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.CONTEXT,
        target_language=None,
        format=ArtifactFormat.JSON,
        created_at="2026-01-26T00:00:07Z",
        location=StorageReference(backend=None, path="/tmp/placeholder.json", uri=None),
        description=None,
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )
    payload = _ArtifactPayload(value="hello")

    stored = asyncio.run(store.write_artifact_json(metadata, payload))
    assert stored.location.path is not None
    Path(stored.location.path).write_text("{not-json", encoding="utf-8")

    with pytest.raises(StorageError) as exc_info:
        asyncio.run(store.load_artifact_json(artifact_id, _ArtifactPayload))
    assert exc_info.value.info.code == StorageErrorCode.SERIALIZATION_ERROR


def test_filesystem_log_store_appends(tmp_path: Path) -> None:
    """Log store appends entries and returns log references."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb605")
    store = FileSystemLogStore(logs_dir=str(tmp_path / "logs"))
    entry = LogEntry(
        timestamp="2026-01-26T00:00:05Z",
        level=LogLevel.INFO,
        event="run_started",
        run_id=run_id,
        phase=None,
        message="Run started",
        data=None,
    )

    asyncio.run(store.append_log(entry))
    reference = asyncio.run(store.get_log_reference(run_id))
    assert reference is not None
    assert reference.location.path is not None


def test_filesystem_log_store_rejects_mixed_run_ids(tmp_path: Path) -> None:
    """Log store rejects mixed run_ids in batch appends."""
    store = FileSystemLogStore(logs_dir=str(tmp_path / "logs"))
    entry_one = LogEntry(
        timestamp="2026-01-26T00:00:08Z",
        level=LogLevel.INFO,
        event="run_started",
        run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb611"),
        phase=None,
        message="Run started",
        data=None,
    )
    entry_two = LogEntry(
        timestamp="2026-01-26T00:00:09Z",
        level=LogLevel.INFO,
        event="run_started",
        run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb612"),
        phase=None,
        message="Run started",
        data=None,
    )

    with pytest.raises(StorageError) as exc_info:
        asyncio.run(store.append_logs([entry_one, entry_two]))
    assert exc_info.value.info.code == StorageErrorCode.VALIDATION_ERROR
