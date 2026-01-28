"""BDD integration tests for storage protocol compliance.

These tests verify that FileSystem storage adapters correctly implement
the defined protocols, ensuring future adapters (e.g., PostgreSQL) can
swap in without breaking the system.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import Field
from pytest_bdd import given, scenarios, then, when

from rentl_core.ports.storage import (
    ArtifactStoreProtocol,
    LogStoreProtocol,
    RunStateStoreProtocol,
)
from rentl_io.storage.filesystem import (
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
    StorageReference,
)
from rentl_schemas.version import VersionInfo

# Link feature file
scenarios("../features/storage/protocol.feature")


class _TestPayload(BaseSchema):
    """Test payload for JSON artifact tests."""

    name: str = Field(..., description="Payload name")
    value: int = Field(..., description="Payload value")


def _build_run_metadata(
    run_id: RunId, status: RunStatus = RunStatus.PENDING
) -> RunMetadata:
    """Build test run metadata.

    Returns:
        RunMetadata with minimal valid structure.
    """
    return RunMetadata(
        run_id=run_id,
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        status=status,
        current_phase=None,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        started_at=None,
        completed_at=None,
    )


def _build_run_state(run_id: RunId, status: RunStatus = RunStatus.PENDING) -> RunState:
    """Build a test run state.

    Returns:
        RunState with minimal valid structure.
    """
    metadata = _build_run_metadata(run_id, status)
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


def _build_run_index_record(
    run_id: RunId, status: RunStatus = RunStatus.PENDING, project_name: str = "test"
) -> RunIndexRecord:
    """Build a test run index record.

    Returns:
        RunIndexRecord with minimal valid structure.
    """
    metadata = _build_run_metadata(run_id, status)
    return RunIndexRecord(
        metadata=metadata,
        project_name=project_name,
        source_language="ja",
        target_languages=["en"],
        updated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        progress=None,
        last_error=None,
    )


class ProtocolContext:
    """Context object for protocol compliance BDD scenarios."""

    workspace_dir: Path | None = None
    run_state_store: FileSystemRunStateStore | None = None
    artifact_store: FileSystemArtifactStore | None = None
    log_store: FileSystemLogStore | None = None
    run_id: RunId | None = None
    saved_index_record: RunIndexRecord | None = None
    listed_records: list[RunIndexRecord] | None = None
    original_payload: _TestPayload | None = None
    loaded_payload: _TestPayload | None = None
    artifact_metadata: ArtifactMetadata | None = None
    artifact_list: list[ArtifactMetadata] | None = None
    log_entry: LogEntry | None = None


# --- Background step ---


@given("an empty workspace directory", target_fixture="ctx")
def given_empty_workspace(tmp_path: Path) -> ProtocolContext:
    """Create an empty workspace directory.

    Returns:
        ProtocolContext with workspace initialized.
    """
    ctx = ProtocolContext()
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()
    ctx.run_id = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb700")
    return ctx


# --- RunStateStoreProtocol tests ---


@given("a FileSystemRunStateStore instance")
def given_run_state_store(ctx: ProtocolContext) -> None:
    """Create a FileSystemRunStateStore instance."""
    assert ctx.workspace_dir is not None
    ctx.run_state_store = FileSystemRunStateStore(
        base_dir=str(ctx.workspace_dir / ".rentl" / "run_state")
    )


@then("the store implements RunStateStoreProtocol")
def then_implements_run_state_protocol(ctx: ProtocolContext) -> None:
    """Assert the store implements RunStateStoreProtocol."""
    assert ctx.run_state_store is not None
    assert isinstance(ctx.run_state_store, RunStateStoreProtocol)


@when("I save a run index record")
def when_save_run_index(ctx: ProtocolContext) -> None:
    """Save a run index record."""
    assert ctx.run_state_store is not None
    assert ctx.run_id is not None

    ctx.saved_index_record = _build_run_index_record(
        ctx.run_id, RunStatus.PENDING, "test-project"
    )
    asyncio.run(ctx.run_state_store.save_run_index(ctx.saved_index_record))


@when("I list run index records")
def when_list_run_index(ctx: ProtocolContext) -> None:
    """List run index records."""
    assert ctx.run_state_store is not None
    ctx.listed_records = asyncio.run(ctx.run_state_store.list_run_index())


@then("the saved index record appears in the list")
def then_index_record_in_list(ctx: ProtocolContext) -> None:
    """Assert the saved index record appears in the list."""
    assert ctx.listed_records is not None
    assert ctx.saved_index_record is not None
    assert len(ctx.listed_records) >= 1
    saved_run_id = ctx.saved_index_record.metadata.run_id
    found = any(r.metadata.run_id == saved_run_id for r in ctx.listed_records)
    assert found, f"Run ID {saved_run_id} not found in list"


@when("I save run index records with different statuses")
def when_save_multiple_indexes(ctx: ProtocolContext) -> None:
    """Save run index records with different statuses."""
    assert ctx.run_state_store is not None
    assert ctx.run_id is not None

    # Save a pending record
    pending_record = _build_run_index_record(
        ctx.run_id, RunStatus.PENDING, "test-pending"
    )
    asyncio.run(ctx.run_state_store.save_run_index(pending_record))

    # Save a completed record with different ID
    completed_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb701")
    completed_record = _build_run_index_record(
        completed_id, RunStatus.COMPLETED, "test-completed"
    )
    asyncio.run(ctx.run_state_store.save_run_index(completed_record))


@when("I list run index records filtered by pending status")
def when_list_filtered_by_status(ctx: ProtocolContext) -> None:
    """List run index records filtered by pending status."""
    assert ctx.run_state_store is not None
    ctx.listed_records = asyncio.run(
        ctx.run_state_store.list_run_index(status=RunStatus.PENDING)
    )


@then("only pending records are returned")
def then_only_pending_records(ctx: ProtocolContext) -> None:
    """Assert only pending records are returned."""
    assert ctx.listed_records is not None
    for record in ctx.listed_records:
        assert record.metadata.status == RunStatus.PENDING, (
            f"Expected PENDING, got {record.metadata.status}"
        )


# --- ArtifactStoreProtocol tests ---


@given("a FileSystemArtifactStore instance")
def given_artifact_store(ctx: ProtocolContext) -> None:
    """Create a FileSystemArtifactStore instance."""
    assert ctx.workspace_dir is not None
    ctx.artifact_store = FileSystemArtifactStore(
        base_dir=str(ctx.workspace_dir / ".rentl" / "artifacts")
    )


@then("the store implements ArtifactStoreProtocol")
def then_implements_artifact_protocol(ctx: ProtocolContext) -> None:
    """Assert the store implements ArtifactStoreProtocol."""
    assert ctx.artifact_store is not None
    assert isinstance(ctx.artifact_store, ArtifactStoreProtocol)


@when("I write a JSON artifact")
def when_write_json_artifact(ctx: ProtocolContext) -> None:
    """Write a JSON artifact."""
    assert ctx.artifact_store is not None
    assert ctx.run_id is not None

    ctx.original_payload = _TestPayload(name="test", value=42)

    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb702")
    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        run_id=ctx.run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.INGEST,
        target_language=None,
        format=ArtifactFormat.JSON,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        location=StorageReference(backend=None, path="/tmp/placeholder.json", uri=None),
        description=None,
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )

    ctx.artifact_metadata = asyncio.run(
        ctx.artifact_store.write_artifact_json(metadata, ctx.original_payload)
    )


@when("I load the JSON artifact")
def when_load_json_artifact(ctx: ProtocolContext) -> None:
    """Load the JSON artifact."""
    assert ctx.artifact_store is not None
    assert ctx.artifact_metadata is not None

    ctx.loaded_payload = asyncio.run(
        ctx.artifact_store.load_artifact_json(
            ctx.artifact_metadata.artifact_id, _TestPayload
        )
    )


@then("the loaded artifact matches the original")
def then_artifact_matches(ctx: ProtocolContext) -> None:
    """Assert the loaded artifact matches the original."""
    assert ctx.original_payload is not None
    assert ctx.loaded_payload is not None
    assert ctx.loaded_payload.name == ctx.original_payload.name
    assert ctx.loaded_payload.value == ctx.original_payload.value


@when("I write multiple artifacts for a run")
def when_write_multiple_artifacts(ctx: ProtocolContext) -> None:
    """Write multiple artifacts for a run."""
    assert ctx.artifact_store is not None
    assert ctx.run_id is not None

    for i in range(3):
        artifact_id: ArtifactId = UUID(f"01890a5c-91c8-7b2a-9f51-9b40d0cfb70{3 + i}")
        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            run_id=ctx.run_id,
            role=ArtifactRole.PHASE_OUTPUT,
            phase=PhaseName.INGEST,
            target_language=None,
            format=ArtifactFormat.JSON,
            created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            location=StorageReference(
                backend=None, path=f"/tmp/placeholder_{i}.json", uri=None
            ),
            description=f"Artifact {i}",
            size_bytes=None,
            checksum_sha256=None,
            metadata=None,
        )
        payload = _TestPayload(name=f"artifact_{i}", value=i)
        asyncio.run(ctx.artifact_store.write_artifact_json(metadata, payload))


@when("I list artifacts for the run")
def when_list_artifacts(ctx: ProtocolContext) -> None:
    """List artifacts for the run."""
    assert ctx.artifact_store is not None
    assert ctx.run_id is not None
    ctx.artifact_list = asyncio.run(ctx.artifact_store.list_artifacts(ctx.run_id))


@then("all artifacts are returned in the list")
def then_all_artifacts_listed(ctx: ProtocolContext) -> None:
    """Assert all artifacts are returned in the list."""
    assert ctx.artifact_list is not None
    assert len(ctx.artifact_list) == 3


# --- LogStoreProtocol tests ---


@given("a FileSystemLogStore instance")
def given_log_store(ctx: ProtocolContext) -> None:
    """Create a FileSystemLogStore instance."""
    assert ctx.workspace_dir is not None
    ctx.log_store = FileSystemLogStore(logs_dir=str(ctx.workspace_dir / "logs"))


@then("the store implements LogStoreProtocol")
def then_implements_log_protocol(ctx: ProtocolContext) -> None:
    """Assert the store implements LogStoreProtocol."""
    assert ctx.log_store is not None
    assert isinstance(ctx.log_store, LogStoreProtocol)


@when("I append a single log entry")
def when_append_single_log(ctx: ProtocolContext) -> None:
    """Append a single log entry."""
    assert ctx.log_store is not None
    assert ctx.run_id is not None

    ctx.log_entry = LogEntry(
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        level=LogLevel.INFO,
        event="protocol_test",
        run_id=ctx.run_id,
        phase=None,
        message="Protocol compliance test log entry",
        data=None,
    )
    asyncio.run(ctx.log_store.append_log(ctx.log_entry))


@when("I get the log reference")
def when_get_log_ref(ctx: ProtocolContext) -> None:
    """Get the log reference - step handled by existing step in test_filesystem.py."""
    # This step is shared with test_filesystem.py, but we need to set up context
    pass


@then("the log file contains the entry")
def then_log_file_contains_entry(ctx: ProtocolContext) -> None:
    """Assert the log file contains the entry."""
    assert ctx.log_store is not None
    assert ctx.run_id is not None
    assert ctx.log_entry is not None

    log_ref = asyncio.run(ctx.log_store.get_log_reference(ctx.run_id))
    assert log_ref is not None
    assert log_ref.location.path is not None

    log_path = Path(log_ref.location.path)
    assert log_path.exists(), f"Log file not found: {log_path}"

    content = log_path.read_text(encoding="utf-8")
    assert "protocol_test" in content
    assert "Protocol compliance test log entry" in content
