"""BDD integration tests for FileSystem storage adapters."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import Field
from pytest_bdd import given, scenarios, then, when

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
    LogFileReference,
    RunStateRecord,
    StorageReference,
)
from rentl_schemas.version import VersionInfo

# Link feature file
scenarios("../features/storage/filesystem.feature")


class _TestRecord(BaseSchema):
    """Test record for JSONL artifact tests."""

    id: str = Field(..., description="Record identifier")
    value: int = Field(..., description="Record value")


def _build_run_state(run_id: RunId) -> RunState:
    """Build a test run state.

    Returns:
        RunState with minimal valid structure.
    """
    metadata = RunMetadata(
        run_id=run_id,
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        status=RunStatus.PENDING,
        current_phase=None,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
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


class StorageContext:
    """Context object for storage BDD scenarios."""

    workspace_dir: Path | None = None
    run_id: RunId | None = None
    run_state: RunState | None = None
    loaded_state: RunState | None = None
    artifact_metadata: ArtifactMetadata | None = None
    original_records: list[_TestRecord] | None = None
    loaded_records: list[_TestRecord] | None = None
    log_reference: LogFileReference | None = None


@given("an empty workspace directory", target_fixture="ctx")
def given_empty_workspace(tmp_path: Path) -> StorageContext:
    """Create an empty workspace directory.

    Returns:
        StorageContext with workspace and run_id initialized.
    """
    ctx = StorageContext()
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()
    ctx.run_id = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb600")
    return ctx


# --- RunStateStore scenarios ---


@when("I save a run state to the store")
def when_save_run_state(ctx: StorageContext) -> None:
    """Save a run state to the store."""
    assert ctx.workspace_dir is not None
    assert ctx.run_id is not None

    store = FileSystemRunStateStore(
        base_dir=str(ctx.workspace_dir / ".rentl" / "run_state")
    )

    ctx.run_state = _build_run_state(ctx.run_id)
    record = RunStateRecord(
        run_id=ctx.run_id,
        stored_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        state=ctx.run_state,
        location=None,
        checksum_sha256=None,
    )
    asyncio.run(store.save_run_state(record))


@when("I load the run state by ID")
def when_load_run_state(ctx: StorageContext) -> None:
    """Load the run state by ID."""
    assert ctx.workspace_dir is not None
    assert ctx.run_id is not None

    store = FileSystemRunStateStore(
        base_dir=str(ctx.workspace_dir / ".rentl" / "run_state")
    )
    record = asyncio.run(store.load_run_state(ctx.run_id))
    if record is not None:
        ctx.loaded_state = record.state


@then("the loaded state matches the saved state")
def then_state_matches(ctx: StorageContext) -> None:
    """Assert the loaded state matches the saved state."""
    assert ctx.run_state is not None
    assert ctx.loaded_state is not None
    assert ctx.loaded_state.metadata.run_id == ctx.run_state.metadata.run_id
    assert ctx.loaded_state.metadata.status == ctx.run_state.metadata.status


# --- ArtifactStore scenarios ---


@when("I write a JSONL artifact with records")
def when_write_artifact(ctx: StorageContext) -> None:
    """Write a JSONL artifact with test records."""
    assert ctx.workspace_dir is not None
    assert ctx.run_id is not None

    store = FileSystemArtifactStore(
        base_dir=str(ctx.workspace_dir / ".rentl" / "artifacts")
    )

    ctx.original_records = [
        _TestRecord(id="a", value=1),
        _TestRecord(id="b", value=2),
        _TestRecord(id="c", value=3),
    ]

    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb601")
    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        run_id=ctx.run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.INGEST,
        target_language=None,
        format=ArtifactFormat.JSONL,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        location=StorageReference(
            backend=None, path="/tmp/placeholder.jsonl", uri=None
        ),
        description=None,
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )

    ctx.artifact_metadata = asyncio.run(
        store.write_artifact_jsonl(metadata, ctx.original_records)
    )


@when("I read the artifact back")
def when_read_artifact(ctx: StorageContext) -> None:
    """Read the artifact back from the store."""
    assert ctx.workspace_dir is not None
    assert ctx.artifact_metadata is not None

    store = FileSystemArtifactStore(
        base_dir=str(ctx.workspace_dir / ".rentl" / "artifacts")
    )

    records = asyncio.run(
        store.load_artifact_jsonl(ctx.artifact_metadata.artifact_id, _TestRecord)
    )
    ctx.loaded_records = list(records)


@then("the records match the originals")
def then_records_match(ctx: StorageContext) -> None:
    """Assert the loaded records match the original records."""
    assert ctx.original_records is not None
    assert ctx.loaded_records is not None
    assert len(ctx.loaded_records) == len(ctx.original_records)
    for loaded, original in zip(ctx.loaded_records, ctx.original_records, strict=True):
        assert loaded.id == original.id
        assert loaded.value == original.value


# --- LogStore scenarios ---


@when("I write log events to a run")
def when_write_log_events(ctx: StorageContext) -> None:
    """Write log events to the store."""
    assert ctx.workspace_dir is not None
    assert ctx.run_id is not None

    store = FileSystemLogStore(logs_dir=str(ctx.workspace_dir / "logs"))

    entries = [
        LogEntry(
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            level=LogLevel.INFO,
            event="test_event",
            run_id=ctx.run_id,
            phase=None,
            message="Test log message",
            data=None,
        ),
    ]

    asyncio.run(store.append_logs(entries))


@when("I get the log reference")
def when_get_log_reference(ctx: StorageContext) -> None:
    """Get the log file reference."""
    assert ctx.workspace_dir is not None
    assert ctx.run_id is not None

    store = FileSystemLogStore(logs_dir=str(ctx.workspace_dir / "logs"))
    ctx.log_reference = asyncio.run(store.get_log_reference(ctx.run_id))


@then("the log file exists at the referenced path")
def then_log_file_exists(ctx: StorageContext) -> None:
    """Assert the log file exists."""
    assert ctx.log_reference is not None
    assert ctx.log_reference.location.path is not None
    log_path = Path(ctx.log_reference.location.path)
    assert log_path.exists(), f"Log file not found: {log_path}"
