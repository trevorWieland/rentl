"""BDD integration tests for FileSystem storage adapters."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import Field
from pytest_bdd import given, scenarios, then, when

from rentl_io.storage import build_log_sink
from rentl_io.storage.filesystem import (
    FileSystemArtifactStore,
    FileSystemLogStore,
    FileSystemRunStateStore,
)
from rentl_schemas.base import BaseSchema
from rentl_schemas.config import LoggingConfig, LogSinkConfig
from rentl_schemas.logs import LogEntry
from rentl_schemas.pipeline import RunMetadata, RunState
from rentl_schemas.primitives import (
    ArtifactId,
    LogLevel,
    LogSinkType,
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
from rentl_schemas.redaction import RedactionConfig, SecretPattern, build_redactor
from rentl_schemas.storage import (
    ArtifactFormat,
    ArtifactMetadata,
    ArtifactRole,
    LogFileReference,
    RunStateRecord,
    StorageReference,
)
from rentl_schemas.version import VersionInfo

pytestmark = pytest.mark.integration

# Link feature file
scenarios("../features/storage/filesystem.feature")


class _TestRecord(BaseSchema):
    """Test record for JSONL artifact tests."""

    id: str = Field(..., description="Record identifier")
    value: int = Field(..., description="Record value")


class _ArtifactRecord(BaseSchema):
    """Test record for artifact redaction tests."""

    name: str = Field(..., description="Record name")
    api_key: str = Field(..., description="API key field")
    metadata: dict[str, str] = Field(..., description="Metadata dict")


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


class RedactionContext:
    """Context object for redaction BDD scenarios."""

    tmp_path: Path | None = None
    log_lines: list[str] | None = None
    artifact_lines: list[str] | None = None
    json_content: str | None = None
    json_payload: dict | None = None


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


# --- Log Redaction scenarios ---


@given("a log store with redaction configured", target_fixture="redaction_ctx")
def given_log_store_with_redaction(tmp_path: Path) -> RedactionContext:
    """Set up a log store with redaction configured.

    Returns:
        RedactionContext with fields initialized.
    """
    ctx = RedactionContext()
    ctx.tmp_path = tmp_path
    return ctx


@when("I write a log entry containing secrets")
def when_write_log_with_secrets(redaction_ctx: RedactionContext) -> None:
    """Write a log entry that contains secrets."""
    assert redaction_ctx.tmp_path is not None

    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb700")
    log_store = FileSystemLogStore(logs_dir=str(redaction_ctx.tmp_path / "logs"))
    logging_config = LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.FILE)])
    config = RedactionConfig(
        patterns=[SecretPattern(pattern=r"sk-[a-zA-Z0-9]{20,}", label="API key")],
        env_var_names=["TEST_SECRET"],
    )
    redactor = build_redactor(config, {"TEST_SECRET": "my-secret-value-123"})
    sink = build_log_sink(logging_config, log_store, redactor=redactor)

    entry = LogEntry(
        timestamp="2026-02-09T12:00:00Z",
        level=LogLevel.INFO,
        event="test_event",
        run_id=run_id,
        phase=None,
        message="Using key sk-abc123def456ghi789jkl012 and value my-secret-value-123",
        data={
            "api_key": "sk-abc123def456ghi789jkl012",
            "secret": "my-secret-value-123",
            "safe": "public-data",
        },
    )

    asyncio.run(sink.emit_log(entry))

    log_file_ref = asyncio.run(log_store.get_log_reference(run_id))
    assert log_file_ref is not None
    assert log_file_ref.location.path is not None
    log_path = Path(log_file_ref.location.path)
    assert log_path.exists()

    redaction_ctx.log_lines = log_path.read_text(encoding="utf-8").strip().splitlines()


@then("the log file redacts API keys and env var values")
def then_log_redacts_secrets(redaction_ctx: RedactionContext) -> None:
    """Assert secrets are redacted in log output."""
    assert redaction_ctx.log_lines is not None
    assert len(redaction_ctx.log_lines) == 2

    redacted_entry = json.loads(redaction_ctx.log_lines[0])
    assert "[REDACTED]" in redacted_entry["message"]
    assert "sk-abc123def456ghi789jkl012" not in redacted_entry["message"]
    assert "my-secret-value-123" not in redacted_entry["message"]
    assert redacted_entry["data"]["api_key"] == "[REDACTED]"
    assert redacted_entry["data"]["secret"] == "[REDACTED]"
    assert redacted_entry["data"]["safe"] == "public-data"


@then("a debug entry records redaction metadata")
def then_debug_entry_records_metadata(redaction_ctx: RedactionContext) -> None:
    """Assert the debug entry records redaction details."""
    assert redaction_ctx.log_lines is not None
    debug_entry = json.loads(redaction_ctx.log_lines[1])
    assert debug_entry["event"] == "redaction_applied"
    assert debug_entry["level"] == "debug"
    assert debug_entry["data"]["original_event"] == "test_event"
    assert debug_entry["data"]["message_redacted"] is True
    assert debug_entry["data"]["data_redacted"] is True


# --- Artifact Redaction scenarios ---


@given("an artifact store with redaction configured", target_fixture="redaction_ctx")
def given_artifact_store_with_redaction(tmp_path: Path) -> RedactionContext:
    """Set up an artifact store with redaction configured.

    Returns:
        RedactionContext with fields initialized.
    """
    ctx = RedactionContext()
    ctx.tmp_path = tmp_path
    return ctx


@when("I write JSONL records containing secrets")
def when_write_jsonl_with_secrets(redaction_ctx: RedactionContext) -> None:
    """Write JSONL artifact records that contain secrets."""
    assert redaction_ctx.tmp_path is not None

    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb800")
    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb801")
    store = FileSystemArtifactStore(base_dir=str(redaction_ctx.tmp_path / "artifacts"))

    config = RedactionConfig(
        patterns=[SecretPattern(pattern=r"sk-[a-zA-Z0-9]{20,}", label="API key")],
        env_var_names=["SECRET_TOKEN"],
    )
    redactor = build_redactor(config, {"SECRET_TOKEN": "token-abc123xyz"})

    records = [
        _ArtifactRecord(
            name="record1",
            api_key="sk-abc123def456ghi789jkl012",
            metadata={"token": "token-abc123xyz", "safe": "public"},
        ),
        _ArtifactRecord(
            name="record2",
            api_key="sk-xyz987wvu654tsr321pqo098",
            metadata={"value": "token-abc123xyz"},
        ),
    ]

    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        run_id=run_id,
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

    stored = asyncio.run(store.write_artifact_jsonl(metadata, records, redactor))
    assert stored.location.path is not None
    artifact_path = Path(stored.location.path)
    assert artifact_path.exists()

    redaction_ctx.artifact_lines = (
        artifact_path.read_text(encoding="utf-8").strip().splitlines()
    )


@then("the stored records have secrets redacted")
def then_jsonl_secrets_redacted(redaction_ctx: RedactionContext) -> None:
    """Assert JSONL records have secrets redacted."""
    assert redaction_ctx.artifact_lines is not None
    assert len(redaction_ctx.artifact_lines) == 2

    record1 = json.loads(redaction_ctx.artifact_lines[0])
    assert record1["name"] == "record1"
    assert record1["api_key"] == "[REDACTED]"
    assert record1["metadata"]["token"] == "[REDACTED]"
    assert record1["metadata"]["safe"] == "public"
    assert "sk-abc123def456ghi789jkl012" not in redaction_ctx.artifact_lines[0]
    assert "token-abc123xyz" not in redaction_ctx.artifact_lines[0]

    record2 = json.loads(redaction_ctx.artifact_lines[1])
    assert record2["name"] == "record2"
    assert record2["api_key"] == "[REDACTED]"
    assert record2["metadata"]["value"] == "[REDACTED]"
    assert "sk-xyz987wvu654tsr321pqo098" not in redaction_ctx.artifact_lines[1]
    assert "token-abc123xyz" not in redaction_ctx.artifact_lines[1]


@then("safe values are preserved")
def then_safe_values_preserved(redaction_ctx: RedactionContext) -> None:
    """Assert safe values remain unchanged in JSONL records."""
    assert redaction_ctx.artifact_lines is not None
    record1 = json.loads(redaction_ctx.artifact_lines[0])
    assert record1["metadata"]["safe"] == "public"


@when("I write a JSON record containing secrets")
def when_write_json_with_secrets(redaction_ctx: RedactionContext) -> None:
    """Write a JSON artifact record that contains secrets."""
    assert redaction_ctx.tmp_path is not None

    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb900")
    artifact_id: ArtifactId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb901")
    store = FileSystemArtifactStore(base_dir=str(redaction_ctx.tmp_path / "artifacts"))

    config = RedactionConfig(
        patterns=[SecretPattern(pattern=r"sk-[a-zA-Z0-9]{20,}", label="API key")],
        env_var_names=["API_SECRET"],
    )
    redactor = build_redactor(config, {"API_SECRET": "secret-value-456"})

    record = _ArtifactRecord(
        name="single-record",
        api_key="sk-abc123def456ghi789jkl012",
        metadata={"secret": "secret-value-456", "public": "data"},
    )

    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        run_id=run_id,
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

    stored = asyncio.run(store.write_artifact_json(metadata, record, redactor))
    assert stored.location.path is not None
    artifact_path = Path(stored.location.path)
    assert artifact_path.exists()

    redaction_ctx.json_content = artifact_path.read_text(encoding="utf-8")
    redaction_ctx.json_payload = json.loads(redaction_ctx.json_content)


@then("the stored record has secrets redacted")
def then_json_secrets_redacted(redaction_ctx: RedactionContext) -> None:
    """Assert JSON record has secrets redacted."""
    assert redaction_ctx.json_payload is not None
    assert redaction_ctx.json_content is not None
    assert redaction_ctx.json_payload["name"] == "single-record"
    assert redaction_ctx.json_payload["api_key"] == "[REDACTED]"
    assert redaction_ctx.json_payload["metadata"]["secret"] == "[REDACTED]"
    assert "sk-abc123def456ghi789jkl012" not in redaction_ctx.json_content
    assert "secret-value-456" not in redaction_ctx.json_content


@then("safe values are preserved in JSON")
def then_safe_values_preserved_json(redaction_ctx: RedactionContext) -> None:
    """Assert safe values remain unchanged in JSON record."""
    assert redaction_ctx.json_payload is not None
    assert redaction_ctx.json_payload["metadata"]["public"] == "data"
