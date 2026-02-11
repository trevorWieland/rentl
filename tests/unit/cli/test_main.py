"""Unit tests for rentl-cli."""

import ast
import asyncio
import inspect
import json
import math
import os
import textwrap
import tomllib
from pathlib import Path
from typing import cast
from uuid import uuid7

import pytest
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_agents.wiring import build_agent_pools
from rentl_cli.main import app
from rentl_core.orchestrator import PipelineOrchestrator
from rentl_core.ports.orchestrator import LogSinkProtocol
from rentl_core.ports.storage import LogStoreProtocol
from rentl_io.storage import FileSystemLogStore
from rentl_io.storage.log_sink import RedactingLogSink, StorageLogSink
from rentl_schemas.config import RunConfig
from rentl_schemas.events import CommandEvent, ProgressEvent
from rentl_schemas.exit_codes import ExitCode
from rentl_schemas.io import SourceLine
from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse
from rentl_schemas.logs import LogEntry
from rentl_schemas.phases import ContextPhaseOutput, SceneSummary
from rentl_schemas.pipeline import PhaseRunRecord, RunMetadata, RunState
from rentl_schemas.primitives import LogLevel, PhaseName, PhaseStatus, RunStatus
from rentl_schemas.progress import (
    AgentStatus,
    AgentTelemetry,
    AgentUsageTotals,
    PhaseProgress,
    ProgressPercentMode,
    ProgressSummary,
    ProgressUpdate,
    RunProgress,
)
from rentl_schemas.redaction import DEFAULT_PATTERNS, RedactionConfig, build_redactor
from rentl_schemas.responses import ApiResponse, RunExecutionResult, RunStatusResult
from rentl_schemas.storage import (
    ArtifactFormat,
    ArtifactMetadata,
    ArtifactRole,
    RunStateRecord,
    StorageBackend,
    StorageReference,
)
from rentl_schemas.version import VersionInfo

runner = CliRunner()


def _read_log_entries(path: Path) -> list[LogEntry]:
    entries: list[LogEntry] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            entries.append(LogEntry.model_validate_json(line))
    return entries


def _log_event_names(entries: list[LogEntry]) -> set[str]:
    return {entry.event for entry in entries}


def test_version_command() -> None:
    """Test version command outputs version string."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_export_command_outputs_warnings(tmp_path: Path) -> None:
    """Export command surfaces warnings in the response."""
    input_path = tmp_path / "translated.jsonl"
    output_path = tmp_path / "output.csv"
    config_path = _write_config(tmp_path, tmp_path)

    payload = {
        "line_id": "line_1",
        "source_text": "Hello",
        "text": "Hello",
        "metadata": None,
    }
    input_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "export",
            "--config",
            str(config_path),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "csv",
            "--untranslated-policy",
            "warn",
            "--include-source-text",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"] is None
    assert response["data"]["summary"]["line_count"] == 1
    assert response["data"]["warnings"][0]["code"] == "untranslated_text"
    assert output_path.exists()


def test_export_emits_command_logs(tmp_path: Path) -> None:
    """Export emits command_started and command_completed logs."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "translated.jsonl"
    output_path = workspace_dir / "output.csv"
    config_path = _write_config(tmp_path, workspace_dir)

    payload = {
        "line_id": "line_1",
        "source_text": "Hello",
        "text": "Hello",
        "metadata": None,
    }
    input_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "export",
            "--config",
            str(config_path),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "csv",
            "--untranslated-policy",
            "warn",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"] is None
    log_files = list((workspace_dir / "logs").glob("*.jsonl"))
    assert len(log_files) == 1
    events = _log_event_names(_read_log_entries(log_files[0]))
    assert CommandEvent.STARTED.value in events
    assert CommandEvent.COMPLETED.value in events


def test_export_validation_error_includes_exit_code(tmp_path: Path) -> None:
    """Export command ValueError handling includes exit_code in error response."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "translated.jsonl"
    output_path = workspace_dir / "output.csv"
    config_path = _write_config(tmp_path, workspace_dir)

    # Invalid JSONL content that will trigger ValueError during parsing
    input_path.write_text("invalid json content\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "export",
            "--config",
            str(config_path),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "csv",
        ],
    )

    assert result.exit_code == 11  # ExitCode.VALIDATION_ERROR
    response = json.loads(result.stdout)
    assert response["error"] is not None
    assert response["error"]["code"] == "validation_error"
    assert response["error"]["exit_code"] is not None
    assert response["error"]["exit_code"] == 11  # ExitCode.VALIDATION_ERROR


def test_run_phase_ingest_persists_state(tmp_path: Path) -> None:
    """Run-phase ingest persists run state/log/progress files."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    config_path = _write_config(tmp_path, workspace_dir)

    result = runner.invoke(
        app,
        [
            "run-phase",
            "--config",
            str(config_path),
            "--phase",
            "ingest",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"] is None
    run_id = response["data"]["run_id"]
    run_state_path = workspace_dir / ".rentl" / "run_state" / "runs" / f"{run_id}.json"
    log_path = workspace_dir / "logs" / f"{run_id}.jsonl"
    progress_path = workspace_dir / "logs" / "progress" / f"{run_id}.jsonl"

    assert run_state_path.exists()
    assert log_path.exists()
    assert progress_path.exists()


def test_run_phase_emits_command_logs(tmp_path: Path) -> None:
    """Run-phase emits command_started and command_completed logs."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    config_path = _write_config(tmp_path, workspace_dir)

    result = runner.invoke(
        app,
        [
            "run-phase",
            "--config",
            str(config_path),
            "--phase",
            "ingest",
        ],
    )

    assert result.exit_code == 0
    response = ApiResponse[RunExecutionResult].model_validate_json(result.stdout)
    assert response.error is None
    assert response.data is not None
    run_id = response.data.run_id
    log_path = workspace_dir / "logs" / f"{run_id}.jsonl"
    assert log_path.exists()

    events = _log_event_names(_read_log_entries(log_path))
    assert CommandEvent.STARTED.value in events
    assert CommandEvent.COMPLETED.value in events


def test_validate_connection_emits_command_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate-connection emits command_started and command_completed logs."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    config_path = _write_config(tmp_path, workspace_dir)

    class _FakeRuntime:
        async def run_prompt(
            self, request: LlmPromptRequest, *, api_key: str
        ) -> LlmPromptResponse:
            return LlmPromptResponse(
                model_id=request.runtime.model.model_id,
                output_text="ok",
            )

    monkeypatch.setenv("TEST_KEY", "fake-key")
    monkeypatch.setattr(cli_main, "_build_llm_runtime", lambda: _FakeRuntime())

    result = runner.invoke(app, ["validate-connection", "--config", str(config_path)])

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"] is None
    log_files = list((workspace_dir / "logs").glob("*.jsonl"))
    assert len(log_files) == 1
    events = _log_event_names(_read_log_entries(log_files[0]))
    assert CommandEvent.STARTED.value in events
    assert CommandEvent.COMPLETED.value in events


def test_run_pipeline_accepts_missing_agents_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run-pipeline validates config without agents section (uses package defaults)."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    config_path = tmp_path / "rentl.toml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            [project]
            schema_version = {{ major = 0, minor = 1, patch = 0 }}
            project_name = "test-project"

            [project.paths]
            workspace_dir = "{workspace_dir}"
            input_path = "input.txt"
            output_dir = "out"
            logs_dir = "logs"

            [project.formats]
            input_format = "txt"
            output_format = "txt"

            [project.languages]
            source_language = "en"
            target_languages = ["ja"]

            [logging]
            [[logging.sinks]]
            type = "file"

            [endpoint]
            provider_name = "test"
            base_url = "http://localhost"
            api_key_env = "TEST_KEY"

            [pipeline.default_model]
            model_id = "gpt-4"

            [[pipeline.phases]]
            phase = "context"
            agents = ["scene_summarizer"]

            [[pipeline.phases]]
            phase = "pretranslation"
            agents = ["idiom_labeler"]

            [[pipeline.phases]]
            phase = "translate"
            agents = ["direct_translator"]

            [[pipeline.phases]]
            phase = "qa"
            agents = ["style_guide_critic"]

            [[pipeline.phases]]
            phase = "edit"
            agents = ["basic_editor"]

            [concurrency]
            max_parallel_requests = 1
            max_parallel_scenes = 1

            [retry]
            max_retries = 1
            backoff_s = 1.0
            max_backoff_s = 2.0

            [cache]
            enabled = false
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("TEST_KEY", "fake-key")

    # Config should load successfully without [agents] section
    config = cli_main._load_resolved_config(config_path)
    assert config.agents is None

    # Verify pipeline resolution to package defaults works end-to-end
    pools = build_agent_pools(config=config)
    assert len(pools.context_agents) == 1
    assert len(pools.pretranslation_agents) == 1
    assert len(pools.translate_agents) == 1
    assert len(pools.qa_agents) == 1
    assert len(pools.edit_agents) == 1


def test_run_pipeline_returns_config_error(tmp_path: Path) -> None:
    """Invalid TOML config yields config_error response."""
    config_path = tmp_path / "rentl.toml"
    config_path.write_text("invalid = [", encoding="utf-8")

    result = runner.invoke(app, ["run-pipeline", "--config", str(config_path)])

    assert result.exit_code == 10  # ExitCode.CONFIG_ERROR
    response = json.loads(result.stdout)
    assert response["error"]["code"] == "config_error"
    assert response["error"]["exit_code"] == 10


def test_status_command_outputs_snapshot(tmp_path: Path) -> None:
    """Status command returns a JSON status snapshot."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)
    run_id = uuid7()

    logs_dir = workspace_dir / "logs"
    progress_dir = logs_dir / "progress"
    progress_dir.mkdir(parents=True)
    progress_path = progress_dir / f"{run_id}.jsonl"

    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.INGEST,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    run_progress = RunProgress(
        phases=[phase_progress],
        summary=summary,
        phase_weights=None,
    )
    update = ProgressUpdate(
        run_id=run_id,
        event=ProgressEvent.RUN_STARTED,
        timestamp="2026-02-03T10:00:00Z",
        phase=PhaseName.INGEST,
        phase_status=PhaseStatus.RUNNING,
        run_progress=run_progress,
        phase_progress=phase_progress,
        metric=None,
        message="Run started",
    )
    progress_path.write_text(update.model_dump_json() + "\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "status",
            "--config",
            str(config_path),
            "--run-id",
            str(run_id),
            "--json",
        ],
    )

    assert result.exit_code == 0
    response = ApiResponse[RunStatusResult].model_validate_json(result.stdout)
    assert response.error is None
    assert response.data is not None
    assert response.data.run_id == run_id


def test_run_pipeline_errors_on_missing_endpoint_key(tmp_path: Path) -> None:
    """Missing API key env var returns config_error response."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    config_path = _write_multi_endpoint_config(tmp_path, workspace_dir)

    result = runner.invoke(app, ["run-pipeline", "--config", str(config_path)])

    assert result.exit_code == 10  # ExitCode.CONFIG_ERROR
    response = json.loads(result.stdout)
    assert response["error"]["code"] == "config_error"
    assert response["error"]["exit_code"] == 10
    assert "SECONDARY_KEY" in response["error"]["message"]


def test_load_or_create_run_context_hydrates_outputs(tmp_path: Path) -> None:
    """Hydration restores phase outputs from stored artifacts."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)
    config = cli_main._load_resolved_config(config_path)
    run_id = uuid7()
    bundle = cli_main._build_storage_bundle(
        config,
        run_id,
        allow_console_logs=False,
    )

    source_lines = [
        SourceLine(
            line_id="line_1",
            route_id=None,
            scene_id="scene_1",
            speaker="A",
            text="Hello",
            metadata=None,
            source_columns=None,
        )
    ]
    context_output = ContextPhaseOutput(
        run_id=run_id,
        phase=PhaseName.CONTEXT,
        project_context=None,
        style_guide=None,
        glossary=None,
        scene_summaries=[
            SceneSummary(scene_id="scene_1", summary="stub", characters=[])
        ],
        context_notes=[],
    )

    ingest_metadata = ArtifactMetadata(
        artifact_id=uuid7(),
        run_id=run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.INGEST,
        target_language=None,
        format=ArtifactFormat.JSONL,
        created_at=cli_main._now_timestamp(),
        location=StorageReference(
            backend=StorageBackend.FILESYSTEM,
            path="placeholder.jsonl",
        ),
        description="ingest",
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )
    ingest_stored = asyncio.run(
        bundle.artifact_store.write_artifact_jsonl(ingest_metadata, source_lines)
    )

    context_metadata = ArtifactMetadata(
        artifact_id=uuid7(),
        run_id=run_id,
        role=ArtifactRole.PHASE_OUTPUT,
        phase=PhaseName.CONTEXT,
        target_language=None,
        format=ArtifactFormat.JSONL,
        created_at=cli_main._now_timestamp(),
        location=StorageReference(
            backend=StorageBackend.FILESYSTEM,
            path="placeholder.jsonl",
        ),
        description="context",
        size_bytes=None,
        checksum_sha256=None,
        metadata=None,
    )
    context_stored = asyncio.run(
        bundle.artifact_store.write_artifact_jsonl(context_metadata, [context_output])
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
                status=PhaseStatus.COMPLETED,
                summary=summary,
                metrics=None,
                started_at=None,
                completed_at=None,
            ),
            PhaseProgress(
                phase=PhaseName.CONTEXT,
                status=PhaseStatus.COMPLETED,
                summary=summary,
                metrics=None,
                started_at=None,
                completed_at=None,
            ),
        ],
        summary=summary,
        phase_weights=None,
    )
    phase_history = [
        PhaseRunRecord(
            phase_run_id=uuid7(),
            phase=PhaseName.INGEST,
            revision=1,
            status=PhaseStatus.COMPLETED,
            target_language=None,
            dependencies=None,
            artifact_ids=[ingest_stored.artifact_id],
            started_at=None,
            completed_at=None,
            stale=False,
            error=None,
            summary=None,
            message="Ingest completed",
        ),
        PhaseRunRecord(
            phase_run_id=uuid7(),
            phase=PhaseName.CONTEXT,
            revision=1,
            status=PhaseStatus.COMPLETED,
            target_language=None,
            dependencies=None,
            artifact_ids=[context_stored.artifact_id],
            started_at=None,
            completed_at=None,
            stale=False,
            error=None,
            summary=None,
            message="Context completed",
        ),
    ]
    run_state = RunState(
        metadata=RunMetadata(
            run_id=run_id,
            schema_version=config.project.schema_version,
            status=RunStatus.RUNNING,
            current_phase=None,
            created_at=cli_main._now_timestamp(),
            started_at=cli_main._now_timestamp(),
            completed_at=None,
        ),
        progress=progress,
        artifacts=[],
        phase_history=phase_history,
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )
    asyncio.run(
        bundle.run_state_store.save_run_state(
            RunStateRecord(
                run_id=run_id,
                stored_at=cli_main._now_timestamp(),
                state=run_state,
                location=None,
                checksum_sha256=None,
            )
        )
    )

    class _NoopLogSink(LogSinkProtocol):
        async def emit_log(self, entry: LogEntry) -> None:
            return None

    orchestrator = PipelineOrchestrator(log_sink=_NoopLogSink())

    run = asyncio.run(
        cli_main._load_or_create_run_context(
            orchestrator,
            bundle,
            run_id,
            config,
        )
    )

    assert run.source_lines is not None
    assert run.source_lines[0].line_id == "line_1"
    assert run.context_output is not None
    assert run.context_output.scene_summaries[0].scene_id == "scene_1"


def test_build_run_report_data_summarizes_usage_and_durations() -> None:
    """Report data aggregates usage and phase durations."""
    run_id = uuid7()
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.TRANSLATE,
        status=PhaseStatus.COMPLETED,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    run_state = RunState(
        metadata=RunMetadata(
            run_id=run_id,
            schema_version=VersionInfo(major=0, minor=1, patch=0),
            status=RunStatus.COMPLETED,
            current_phase=None,
            created_at="2026-02-03T10:00:00Z",
            started_at="2026-02-03T10:00:00Z",
            completed_at="2026-02-03T10:00:10Z",
        ),
        progress=RunProgress(
            phases=[phase_progress],
            summary=summary,
            phase_weights=None,
        ),
        artifacts=[],
        phase_history=[
            PhaseRunRecord(
                phase_run_id=uuid7(),
                phase=PhaseName.TRANSLATE,
                revision=1,
                status=PhaseStatus.COMPLETED,
                target_language="ja",
                dependencies=None,
                artifact_ids=None,
                started_at="2026-02-03T10:00:00Z",
                completed_at="2026-02-03T10:00:05Z",
                stale=False,
                error=None,
                summary=None,
                message="Translate completed",
            )
        ],
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )
    progress_updates = [
        ProgressUpdate(
            run_id=run_id,
            event=ProgressEvent.AGENT_COMPLETED,
            timestamp="2026-02-03T10:00:05Z",
            phase=PhaseName.TRANSLATE,
            phase_status=PhaseStatus.COMPLETED,
            run_progress=None,
            phase_progress=None,
            metric=None,
            agent_update=AgentTelemetry(
                agent_run_id="agent_1",
                agent_name="direct_translator",
                phase=PhaseName.TRANSLATE,
                target_language="ja",
                status=AgentStatus.COMPLETED,
                attempt=1,
                started_at="2026-02-03T10:00:00Z",
                completed_at="2026-02-03T10:00:05Z",
                usage=AgentUsageTotals(
                    input_tokens=100,
                    output_tokens=200,
                    total_tokens=300,
                    request_count=1,
                    tool_calls=0,
                ),
                message="done",
            ),
            message="agent",
        )
    ]

    data = cli_main._build_run_report_data(
        run_id=run_id,
        run_state=run_state,
        progress_updates=progress_updates,
    )

    token_usage = cast(dict[str, int], data["token_usage"])
    phase_durations = cast(list[dict[str, float]], data["phase_durations_s"])
    assert token_usage["total_tokens"] == 300
    assert phase_durations[0]["duration_s"] == 5.0


def test_write_run_report_writes_json(tmp_path: Path) -> None:
    """Report writer creates the report file on disk."""
    run_id = uuid7()
    report_path = cli_main._report_path(str(tmp_path), run_id)
    cli_main._write_run_report(report_path, {"run_id": str(run_id)})

    assert report_path.exists()
    assert str(run_id) in report_path.read_text(encoding="utf-8")


def test_aggregate_usage_ignores_non_completed_updates() -> None:
    """Usage aggregation skips non-completed updates."""
    run_id = uuid7()
    updates = [
        ProgressUpdate(
            run_id=run_id,
            event=ProgressEvent.AGENT_STARTED,
            timestamp="2026-02-03T10:00:00Z",
            phase=PhaseName.TRANSLATE,
            phase_status=PhaseStatus.RUNNING,
            run_progress=None,
            phase_progress=None,
            metric=None,
            agent_update=AgentTelemetry(
                agent_run_id="agent_1",
                agent_name="direct_translator",
                phase=PhaseName.TRANSLATE,
                target_language="ja",
                status=AgentStatus.RUNNING,
                attempt=1,
                started_at="2026-02-03T10:00:00Z",
                completed_at=None,
                usage=None,
                message="start",
            ),
            message="agent",
        )
    ]

    total, by_phase = cli_main._aggregate_usage(updates)

    assert total is None
    assert by_phase == {}


def test_aggregate_usage_with_completed_update() -> None:
    """Usage aggregation sums completed updates."""
    run_id = uuid7()
    updates = [
        ProgressUpdate(
            run_id=run_id,
            event=ProgressEvent.AGENT_COMPLETED,
            timestamp="2026-02-03T10:00:05Z",
            phase=PhaseName.TRANSLATE,
            phase_status=PhaseStatus.COMPLETED,
            run_progress=None,
            phase_progress=None,
            metric=None,
            agent_update=AgentTelemetry(
                agent_run_id="agent_1",
                agent_name="direct_translator",
                phase=PhaseName.TRANSLATE,
                target_language="ja",
                status=AgentStatus.COMPLETED,
                attempt=1,
                started_at="2026-02-03T10:00:00Z",
                completed_at="2026-02-03T10:00:05Z",
                usage=AgentUsageTotals(
                    input_tokens=10,
                    output_tokens=20,
                    total_tokens=30,
                    request_count=1,
                    tool_calls=0,
                ),
                message="done",
            ),
            message="agent",
        )
    ]

    total, by_phase = cli_main._aggregate_usage(updates)

    assert total is not None
    assert total.total_tokens == 30
    assert by_phase[PhaseName.TRANSLATE, "ja"].output_tokens == 20


def test_build_run_report_data_without_run_state() -> None:
    """Report data handles missing run state."""
    run_id = uuid7()
    data = cli_main._build_run_report_data(
        run_id=run_id,
        run_state=None,
        progress_updates=[],
    )

    assert data["run_id"] == str(run_id)
    assert data["token_usage"] is None


def test_duration_seconds_handles_invalid_inputs() -> None:
    """Duration helper returns None for invalid timestamps."""
    assert cli_main._duration_seconds("invalid", "2026-02-03T10:00:00Z") is None
    assert cli_main._duration_seconds("2026-02-03T10:00:00Z", "invalid") is None


def test_duration_seconds_handles_valid_inputs() -> None:
    """Duration helper returns seconds for valid timestamps."""
    assert (
        cli_main._duration_seconds("2026-02-03T10:00:00Z", "2026-02-03T10:00:10Z")
        == 10.0
    )


def test_read_progress_updates_since(tmp_path: Path) -> None:
    """Progress reader returns updates and new offsets."""
    run_id = uuid7()
    progress_path = tmp_path / "progress.jsonl"
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress_running = PhaseProgress(
        phase=PhaseName.INGEST,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    phase_progress_completed = PhaseProgress(
        phase=PhaseName.INGEST,
        status=PhaseStatus.COMPLETED,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    run_progress_running = RunProgress(
        phases=[phase_progress_running],
        summary=summary,
        phase_weights=None,
    )
    run_progress_completed = RunProgress(
        phases=[phase_progress_completed],
        summary=summary,
        phase_weights=None,
    )
    updates = [
        ProgressUpdate(
            run_id=run_id,
            event=ProgressEvent.RUN_STARTED,
            timestamp="2026-02-03T10:00:00Z",
            phase=PhaseName.INGEST,
            phase_status=PhaseStatus.RUNNING,
            run_progress=run_progress_running,
            phase_progress=phase_progress_running,
            metric=None,
            agent_update=None,
            message="start",
        ),
        ProgressUpdate(
            run_id=run_id,
            event=ProgressEvent.RUN_COMPLETED,
            timestamp="2026-02-03T10:00:10Z",
            phase=PhaseName.INGEST,
            phase_status=PhaseStatus.COMPLETED,
            run_progress=run_progress_completed,
            phase_progress=phase_progress_completed,
            metric=None,
            agent_update=None,
            message="done",
        ),
    ]
    progress_path.write_text(
        "\n".join(update.model_dump_json() for update in updates) + "\n",
        encoding="utf-8",
    )

    chunk, offset = cli_main._read_progress_updates_since(progress_path, 0)
    assert len(chunk) == 2
    assert offset > 0


def test_read_progress_updates(tmp_path: Path) -> None:
    """Progress reader returns parsed updates."""
    run_id = uuid7()
    progress_path = tmp_path / "progress.jsonl"
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.INGEST,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    run_progress = RunProgress(
        phases=[phase_progress],
        summary=summary,
        phase_weights=None,
    )
    update = ProgressUpdate(
        run_id=run_id,
        event=ProgressEvent.RUN_STARTED,
        timestamp="2026-02-03T10:00:00Z",
        phase=PhaseName.INGEST,
        phase_status=PhaseStatus.RUNNING,
        run_progress=run_progress,
        phase_progress=phase_progress,
        metric=None,
        agent_update=None,
        message="start",
    )
    progress_path.write_text(update.model_dump_json() + "\n", encoding="utf-8")

    updates = cli_main._read_progress_updates(progress_path)
    assert len(updates) == 1
    assert updates[0].event == ProgressEvent.RUN_STARTED


def test_render_run_execution_summary_does_not_crash(tmp_path: Path) -> None:
    """Run summary renderer handles report generation paths."""
    run_id = uuid7()
    progress_path = tmp_path / "progress.jsonl"
    progress_path.write_text("", encoding="utf-8")
    run_state = RunState(
        metadata=RunMetadata(
            run_id=run_id,
            schema_version=VersionInfo(major=0, minor=1, patch=0),
            status=RunStatus.COMPLETED,
            current_phase=None,
            created_at="2026-02-03T10:00:00Z",
            started_at="2026-02-03T10:00:00Z",
            completed_at="2026-02-03T10:00:10Z",
        ),
        progress=RunProgress(
            phases=[
                PhaseProgress(
                    phase=PhaseName.INGEST,
                    status=PhaseStatus.COMPLETED,
                    summary=ProgressSummary(
                        percent_complete=None,
                        percent_mode=ProgressPercentMode.UNAVAILABLE,
                        eta_seconds=None,
                        notes=None,
                    ),
                    metrics=None,
                    started_at=None,
                    completed_at=None,
                )
            ],
            summary=ProgressSummary(
                percent_complete=None,
                percent_mode=ProgressPercentMode.UNAVAILABLE,
                eta_seconds=None,
                notes=None,
            ),
            phase_weights=None,
        ),
        artifacts=[],
        phase_history=None,
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )
    result = RunExecutionResult(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        progress=run_state.progress.summary,
        run_state=run_state,
        log_file=None,
        progress_file=StorageReference(
            backend=StorageBackend.FILESYSTEM,
            path=str(progress_path),
        ),
        phase_record=None,
    )

    cli_main._render_run_execution_summary(result, console=None)


def test_render_run_execution_summary_next_steps_export_needed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Run summary shows export command when export phase not run."""
    run_id = uuid7()
    progress_path = tmp_path / "progress.jsonl"
    progress_path.write_text("", encoding="utf-8")
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)
    config = cli_main._load_resolved_config(config_path)

    run_state = RunState(
        metadata=RunMetadata(
            run_id=run_id,
            schema_version=VersionInfo(major=0, minor=1, patch=0),
            status=RunStatus.COMPLETED,
            current_phase=None,
            created_at="2026-02-03T10:00:00Z",
            started_at="2026-02-03T10:00:00Z",
            completed_at="2026-02-03T10:00:10Z",
        ),
        progress=RunProgress(
            phases=[
                PhaseProgress(
                    phase=PhaseName.TRANSLATE,
                    status=PhaseStatus.COMPLETED,
                    summary=ProgressSummary(
                        percent_complete=None,
                        percent_mode=ProgressPercentMode.UNAVAILABLE,
                        eta_seconds=None,
                        notes=None,
                    ),
                    metrics=None,
                    started_at=None,
                    completed_at=None,
                )
            ],
            summary=ProgressSummary(
                percent_complete=None,
                percent_mode=ProgressPercentMode.UNAVAILABLE,
                eta_seconds=None,
                notes=None,
            ),
            phase_weights=None,
        ),
        artifacts=[],
        phase_history=[
            PhaseRunRecord(
                phase_run_id=uuid7(),
                phase=PhaseName.TRANSLATE,
                revision=1,
                status=PhaseStatus.COMPLETED,
                target_language="es",
                dependencies=None,
                artifact_ids=None,
                started_at="2026-02-03T10:00:00Z",
                completed_at="2026-02-03T10:00:10Z",
                stale=False,
                error=None,
                summary=None,
                message=None,
            )
        ],
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )
    result = RunExecutionResult(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        progress=run_state.progress.summary,
        run_state=run_state,
        log_file=None,
        progress_file=StorageReference(
            backend=StorageBackend.FILESYSTEM,
            path=str(progress_path),
        ),
        phase_record=None,
    )

    cli_main._render_run_execution_summary(result, console=None, config=config)

    captured = capsys.readouterr()
    assert "Next Steps" in captured.out
    assert "rentl export" in captured.out
    assert "out" in captured.out


def test_render_run_execution_summary_next_steps_export_complete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Run summary shows output directory when export phase completed."""
    run_id = uuid7()
    progress_path = tmp_path / "progress.jsonl"
    progress_path.write_text("", encoding="utf-8")
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)
    config = cli_main._load_resolved_config(config_path)

    run_state = RunState(
        metadata=RunMetadata(
            run_id=run_id,
            schema_version=VersionInfo(major=0, minor=1, patch=0),
            status=RunStatus.COMPLETED,
            current_phase=None,
            created_at="2026-02-03T10:00:00Z",
            started_at="2026-02-03T10:00:00Z",
            completed_at="2026-02-03T10:00:10Z",
        ),
        progress=RunProgress(
            phases=[
                PhaseProgress(
                    phase=PhaseName.EXPORT,
                    status=PhaseStatus.COMPLETED,
                    summary=ProgressSummary(
                        percent_complete=None,
                        percent_mode=ProgressPercentMode.UNAVAILABLE,
                        eta_seconds=None,
                        notes=None,
                    ),
                    metrics=None,
                    started_at=None,
                    completed_at=None,
                )
            ],
            summary=ProgressSummary(
                percent_complete=None,
                percent_mode=ProgressPercentMode.UNAVAILABLE,
                eta_seconds=None,
                notes=None,
            ),
            phase_weights=None,
        ),
        artifacts=[],
        phase_history=[
            PhaseRunRecord(
                phase_run_id=uuid7(),
                phase=PhaseName.EXPORT,
                revision=1,
                status=PhaseStatus.COMPLETED,
                target_language=None,
                dependencies=None,
                artifact_ids=None,
                started_at="2026-02-03T10:00:00Z",
                completed_at="2026-02-03T10:00:10Z",
                stale=False,
                error=None,
                summary=None,
                message=None,
            )
        ],
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )
    result = RunExecutionResult(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        progress=run_state.progress.summary,
        run_state=run_state,
        log_file=None,
        progress_file=StorageReference(
            backend=StorageBackend.FILESYSTEM,
            path=str(progress_path),
        ),
        phase_record=None,
    )

    cli_main._render_run_execution_summary(result, console=None, config=config)

    captured = capsys.readouterr()
    assert "Next Steps" in captured.out
    assert "Export complete!" in captured.out
    assert "Output files:" in captured.out


def _write_config(tmp_path: Path, workspace_dir: Path) -> Path:
    config_path = tmp_path / "rentl.toml"
    content = textwrap.dedent(
        f"""
        [project]
        schema_version = {{ major = 0, minor = 1, patch = 0 }}
        project_name = "test-project"

        [project.paths]
        workspace_dir = "{workspace_dir}"
        input_path = "input.txt"
        output_dir = "out"
        logs_dir = "logs"

        [project.formats]
        input_format = "txt"
        output_format = "txt"

        [project.languages]
        source_language = "en"
        target_languages = ["ja"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [agents]
        prompts_dir = "{workspace_dir}/prompts"
        agents_dir = "{workspace_dir}/agents"

        [endpoint]
        provider_name = "test"
        base_url = "http://localhost"
        api_key_env = "TEST_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"

        [[pipeline.phases]]
        phase = "ingest"

        [[pipeline.phases]]
        phase = "context"
        agents = ["context_agent"]

        [[pipeline.phases]]
        phase = "pretranslation"
        agents = ["pretranslation_agent"]

        [[pipeline.phases]]
        phase = "translate"
        agents = ["translate_agent"]

        [[pipeline.phases]]
        phase = "qa"
        agents = ["qa_agent"]

        [[pipeline.phases]]
        phase = "edit"
        agents = ["edit_agent"]

        [[pipeline.phases]]
        phase = "export"

        [concurrency]
        max_parallel_requests = 1
        max_parallel_scenes = 1

        [retry]
        max_retries = 1
        backoff_s = 1.0
        max_backoff_s = 2.0

        [cache]
        enabled = false
        """
    ).strip()
    config_path.write_text(content + "\n", encoding="utf-8")
    return config_path


def _write_multi_endpoint_config(tmp_path: Path, workspace_dir: Path) -> Path:
    config_path = tmp_path / "rentl.toml"
    content = textwrap.dedent(
        f"""
        [project]
        schema_version = {{ major = 0, minor = 1, patch = 0 }}
        project_name = "test-project"

        [project.paths]
        workspace_dir = "{workspace_dir}"
        input_path = "input.txt"
        output_dir = "out"
        logs_dir = "logs"

        [project.formats]
        input_format = "txt"
        output_format = "txt"

        [project.languages]
        source_language = "en"
        target_languages = ["ja"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [agents]
        prompts_dir = "{workspace_dir}/prompts"
        agents_dir = "{workspace_dir}/agents"

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "http://localhost"
        api_key_env = "PRIMARY_KEY"

        [[endpoints.endpoints]]
        provider_name = "secondary"
        base_url = "http://localhost:8002/api/v1"
        api_key_env = "SECONDARY_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"
        endpoint_ref = "secondary"

        [[pipeline.phases]]
        phase = "ingest"

        [[pipeline.phases]]
        phase = "context"
        agents = ["scene_summarizer"]

        [[pipeline.phases]]
        phase = "pretranslation"
        agents = ["idiom_labeler"]

        [[pipeline.phases]]
        phase = "translate"
        agents = ["direct_translator"]

        [[pipeline.phases]]
        phase = "qa"
        agents = ["style_guide_critic"]

        [[pipeline.phases]]
        phase = "edit"
        agents = ["basic_editor"]

        [[pipeline.phases]]
        phase = "export"

        [concurrency]
        max_parallel_requests = 1
        max_parallel_scenes = 1

        [retry]
        max_retries = 1
        backoff_s = 1.0
        max_backoff_s = 2.0

        [cache]
        enabled = false
        """
    ).strip()
    config_path.write_text(content + "\n", encoding="utf-8")
    return config_path


def test_status_json_failed_returns_orchestration_exit_code(tmp_path: Path) -> None:
    """Status --json with FAILED status returns exit code 20 and valid JSON response."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)
    run_id = uuid7()

    # Create run state with FAILED status
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.INGEST,
        status=PhaseStatus.FAILED,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    run_state = RunState(
        metadata=RunMetadata(
            run_id=run_id,
            schema_version=VersionInfo(major=0, minor=1, patch=0),
            status=RunStatus.FAILED,
            current_phase=None,
            created_at="2026-02-03T10:00:00Z",
            started_at="2026-02-03T10:00:00Z",
            completed_at="2026-02-03T10:00:10Z",
        ),
        progress=RunProgress(
            phases=[phase_progress],
            summary=summary,
            phase_weights=None,
        ),
        artifacts=[],
        phase_history=None,
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )

    run_state_dir = workspace_dir / ".rentl" / "run_state" / "runs"
    run_state_dir.mkdir(parents=True)
    run_state_path = run_state_dir / f"{run_id}.json"

    run_state_record = RunStateRecord(
        run_id=run_id,
        stored_at="2026-02-03T10:00:10Z",
        state=run_state,
        location=None,
        checksum_sha256=None,
    )
    run_state_path.write_text(run_state_record.model_dump_json(), encoding="utf-8")

    # Create empty progress file
    progress_dir = workspace_dir / "logs" / "progress"
    progress_dir.mkdir(parents=True)
    progress_path = progress_dir / f"{run_id}.jsonl"
    progress_path.write_text("", encoding="utf-8")

    # Create empty log file
    log_dir = workspace_dir / "logs"
    log_path = log_dir / f"{run_id}.jsonl"
    log_path.write_text("", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "status",
            "--config",
            str(config_path),
            "--run-id",
            str(run_id),
            "--json",
        ],
    )

    # Assert exit code is ORCHESTRATION_ERROR (20)
    assert result.exit_code == 20
    # Assert output is valid JSON with data, not an error envelope
    response = ApiResponse[RunStatusResult].model_validate_json(result.stdout)
    assert response.error is None
    assert response.data is not None
    assert response.data.status == RunStatus.FAILED


def test_status_json_cancelled_returns_orchestration_exit_code(tmp_path: Path) -> None:
    """Status --json with CANCELLED status returns exit code 20, valid JSON."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)
    run_id = uuid7()

    # Create run state with CANCELLED status
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    phase_progress = PhaseProgress(
        phase=PhaseName.INGEST,
        status=PhaseStatus.RUNNING,
        summary=summary,
        metrics=None,
        started_at=None,
        completed_at=None,
    )
    run_state = RunState(
        metadata=RunMetadata(
            run_id=run_id,
            schema_version=VersionInfo(major=0, minor=1, patch=0),
            status=RunStatus.CANCELLED,
            current_phase=None,
            created_at="2026-02-03T10:00:00Z",
            started_at="2026-02-03T10:00:00Z",
            completed_at="2026-02-03T10:00:10Z",
        ),
        progress=RunProgress(
            phases=[phase_progress],
            summary=summary,
            phase_weights=None,
        ),
        artifacts=[],
        phase_history=None,
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )

    run_state_dir = workspace_dir / ".rentl" / "run_state" / "runs"
    run_state_dir.mkdir(parents=True)
    run_state_path = run_state_dir / f"{run_id}.json"

    run_state_record = RunStateRecord(
        run_id=run_id,
        stored_at="2026-02-03T10:00:10Z",
        state=run_state,
        location=None,
        checksum_sha256=None,
    )
    run_state_path.write_text(run_state_record.model_dump_json(), encoding="utf-8")

    # Create empty progress file
    progress_dir = workspace_dir / "logs" / "progress"
    progress_dir.mkdir(parents=True)
    progress_path = progress_dir / f"{run_id}.jsonl"
    progress_path.write_text("", encoding="utf-8")

    # Create empty log file
    log_dir = workspace_dir / "logs"
    log_path = log_dir / f"{run_id}.jsonl"
    log_path.write_text("", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "status",
            "--config",
            str(config_path),
            "--run-id",
            str(run_id),
            "--json",
        ],
    )

    # Assert exit code is ORCHESTRATION_ERROR (20)
    assert result.exit_code == 20
    # Assert output is valid JSON with data, not an error envelope
    response = ApiResponse[RunStatusResult].model_validate_json(result.stdout)
    assert response.error is None
    assert response.data is not None
    assert response.data.status == RunStatus.CANCELLED


def test_no_hardcoded_exit_codes() -> None:
    """Verify no hardcoded integer exit codes remain in CLI code.

    All exit codes must reference the ExitCode enum or response.error.exit_code.
    """
    # Get the source code of the main module
    main_source = inspect.getsource(cli_main)
    tree = ast.parse(main_source)

    # Find all typer.Exit() calls
    hardcoded_exits = []

    class ExitCodeVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            # Check if this is a typer.Exit call
            if isinstance(node.func, ast.Attribute) and (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "typer"
                and node.func.attr == "Exit"
            ):
                # Check if code argument is a hardcoded integer
                # Allow exit code 1 for check-secrets (scanner convention)
                for keyword in node.keywords:
                    if (
                        keyword.arg == "code"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, int)
                        and keyword.value.value != 1  # Allow exit 1 for check-secrets
                    ):
                        hardcoded_exits.append((
                            getattr(node, "lineno", "unknown"),
                            keyword.value.value,
                        ))
            self.generic_visit(node)

    visitor = ExitCodeVisitor()
    visitor.visit(tree)

    assert not hardcoded_exits, (
        f"Found hardcoded integer exit codes at lines: {hardcoded_exits}. "
        "All exit codes must use ExitCode enum or response.error.exit_code."
    )


def test_init_command_happy_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command with default answers creates valid project structure."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Mock prompts to accept defaults
    inputs = [
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        "",  # target_languages (default: en)
        "",  # provider_name (default: openrouter)
        "",  # base_url (default: https://openrouter.ai/api/v1)
        "",  # api_key_env (default: OPENROUTER_API_KEY)
        "",  # model_id (default: openai/gpt-4.1)
        "",  # input_format (default: jsonl)
        "",  # include_seed_data (default: yes)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert successful exit
    assert result.exit_code == 0

    # Verify created files
    assert (tmp_path / "rentl.toml").exists()
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "input").is_dir()
    assert (tmp_path / "out").is_dir()
    assert (tmp_path / "logs").is_dir()
    # Game name defaults to directory name (tmp_path.name)
    expected_seed_file = tmp_path / "input" / f"{tmp_path.name}.jsonl"
    assert expected_seed_file.exists(), f"Expected seed file: {expected_seed_file}"

    # Verify output contains success information
    assert "rentl init" in result.stdout
    assert "rentl.toml" in result.stdout
    assert ".env" in result.stdout


def test_init_command_overwrite_confirmation_accept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command asks for confirmation when rentl.toml exists and accepts."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create existing rentl.toml
    (tmp_path / "rentl.toml").write_text("[project]\n", encoding="utf-8")

    # Mock prompts: confirm overwrite, then accept defaults
    inputs = [
        "y",  # overwrite confirmation
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        "",  # target_languages (default: en)
        "",  # provider_name (default: openrouter)
        "",  # base_url (default: https://openrouter.ai/api/v1)
        "",  # api_key_env (default: OPENROUTER_API_KEY)
        "",  # model_id (default: openai/gpt-4.1)
        "",  # input_format (default: jsonl)
        "",  # include_seed_data (default: yes)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert successful exit
    assert result.exit_code == 0

    # Verify output contains overwrite warning
    assert "already exists" in result.stdout.lower()

    # Verify new files were created
    assert (tmp_path / "rentl.toml").exists()
    assert (tmp_path / ".env").exists()


def test_init_command_overwrite_confirmation_cancel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command cancels cleanly when user declines overwrite."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create existing rentl.toml
    original_content = "[project]\nproject_name = 'original'\n"
    (tmp_path / "rentl.toml").write_text(original_content, encoding="utf-8")

    # Mock prompts: decline overwrite
    inputs = [
        "n",  # decline overwrite
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert clean exit (code 0 for cancellation)
    assert result.exit_code == 0

    # Verify output contains cancellation message
    assert "Cancelled" in result.stdout or "cancelled" in result.stdout.lower()

    # Verify original file was NOT modified
    assert (tmp_path / "rentl.toml").read_text(encoding="utf-8") == original_content

    # Verify no new directories were created
    assert not (tmp_path / "input").exists()
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "logs").exists()
    assert not (tmp_path / ".env").exists()


def test_init_command_target_languages_trailing_comma(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command sanitizes trailing comma in target languages."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Mock prompts with trailing comma in target languages
    inputs = [
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        "en,",  # target_languages with trailing comma
        "",  # provider_name (default: openrouter)
        "",  # base_url (default: https://openrouter.ai/api/v1)
        "",  # api_key_env (default: OPENROUTER_API_KEY)
        "",  # model_id (default: openai/gpt-4.1)
        "",  # input_format (default: jsonl)
        "",  # include_seed_data (default: yes)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert successful exit
    assert result.exit_code == 0

    # Verify generated config is valid
    config_path = tmp_path / "rentl.toml"
    assert config_path.exists()

    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)

    config = RunConfig.model_validate(config_dict, strict=True)
    assert config.project.languages.target_languages == ["en"]


def test_init_command_target_languages_multiple_with_spaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command handles multiple target languages with spaces."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Mock prompts with multiple languages and spaces
    inputs = [
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        "en, fr",  # target_languages with spaces
        "",  # provider_name (default: openrouter)
        "",  # base_url (default: https://openrouter.ai/api/v1)
        "",  # api_key_env (default: OPENROUTER_API_KEY)
        "",  # model_id (default: openai/gpt-4.1)
        "",  # input_format (default: jsonl)
        "",  # include_seed_data (default: yes)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert successful exit
    assert result.exit_code == 0

    # Verify generated config is valid
    config_path = tmp_path / "rentl.toml"
    assert config_path.exists()

    with config_path.open("rb") as f:
        config_dict = tomllib.load(f)

    config = RunConfig.model_validate(config_dict, strict=True)
    assert config.project.languages.target_languages == ["en", "fr"]


def test_init_command_target_languages_blank_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command fails fast on blank target languages input."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Mock prompts with blank target languages (just commas)
    inputs = [
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        ",",  # target_languages blank (just comma)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert validation error exit code
    assert result.exit_code == ExitCode.VALIDATION_ERROR.value

    # Verify error message is shown
    assert "at least one target language" in result.stdout.lower()

    # Verify no files were created
    assert not (tmp_path / "rentl.toml").exists()
    assert not (tmp_path / ".env").exists()


def test_init_command_provider_preset_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command with provider preset selection (OpenRouter, OpenAI, Ollama)."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Test selecting preset 1 (OpenRouter)
    inputs = [
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        "",  # target_languages (default: en)
        "1",  # provider choice: OpenRouter
        "",  # input_format (default: jsonl)
        "",  # include_seed_data (default: yes)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert successful exit
    assert result.exit_code == 0
    assert "OpenRouter" in result.stdout
    assert "https://openrouter.ai/api/v1" in result.stdout

    # Verify rentl.toml contains correct provider settings
    config_path = tmp_path / "rentl.toml"
    assert config_path.exists()
    with config_path.open("rb") as f:
        config = tomllib.load(f)
    assert config["endpoint"]["base_url"] == "https://openrouter.ai/api/v1"
    assert config["endpoint"]["api_key_env"] == "OPENROUTER_API_KEY"


def test_init_command_provider_custom_option(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command with custom provider option (choice 4)."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Test selecting custom option (preset count is 3, so custom is 4)
    inputs = [
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        "",  # target_languages (default: en)
        "4",  # provider choice: Custom
        "mycustom",  # custom provider name
        "https://api.example.com/v1",  # custom base URL
        "MY_API_KEY",  # custom API key env var
        "my-model-v1",  # custom model ID
        "",  # input_format (default: jsonl)
        "",  # include_seed_data (default: yes)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert successful exit
    assert result.exit_code == 0

    # Verify rentl.toml contains custom provider settings
    config_path = tmp_path / "rentl.toml"
    assert config_path.exists()
    with config_path.open("rb") as f:
        config = tomllib.load(f)
    assert config["endpoint"]["base_url"] == "https://api.example.com/v1"
    assert config["endpoint"]["api_key_env"] == "MY_API_KEY"
    assert config["pipeline"]["default_model"]["model_id"] == "my-model-v1"


def test_init_command_provider_out_of_range_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command rejects out-of-range provider choice."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Test with out-of-range numeric input (e.g., 999)
    inputs = [
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        "",  # target_languages (default: en)
        "999",  # provider choice: out of range (should fail)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert validation error exit code
    assert result.exit_code == ExitCode.VALIDATION_ERROR.value

    # Verify error message indicates valid range
    assert "between 1 and" in result.stdout.lower()

    # Verify no files were created
    assert not (tmp_path / "rentl.toml").exists()
    assert not (tmp_path / ".env").exists()


def test_init_command_custom_url_validation_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test init command validates custom URL format and loops on invalid input."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Test with invalid URL followed by valid URL
    inputs = [
        "",  # project_name (default)
        "",  # game_name (default)
        "",  # source_language (default: ja)
        "",  # target_languages (default: en)
        "4",  # provider choice: Custom
        "mycustom",  # custom provider name
        "not-a-url",  # invalid base URL (should fail validation and loop)
        "https://api.example.com/v1",  # valid base URL (second attempt)
        "MY_API_KEY",  # custom API key env var
        "my-model-v1",  # custom model ID
        "",  # input_format (default: jsonl)
        "",  # include_seed_data (default: yes)
    ]
    input_str = "\n".join(inputs) + "\n"

    result = runner.invoke(app, ["init"], input=input_str)

    # Assert successful exit (validation loop allows retry)
    assert result.exit_code == 0

    # Verify error message appeared for invalid URL
    assert "error" in result.stdout.lower()

    # Verify rentl.toml was created with valid URL
    config_path = tmp_path / "rentl.toml"
    assert config_path.exists()
    with config_path.open("rb") as f:
        config = tomllib.load(f)
    assert config["endpoint"]["base_url"] == "https://api.example.com/v1"


def test_help_command_no_args() -> None:
    """Test help command without arguments lists all commands."""
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0
    # Should list core commands
    assert "version" in result.stdout
    assert "init" in result.stdout
    assert "doctor" in result.stdout
    assert "help" in result.stdout


def test_help_command_with_valid_command() -> None:
    """Test help command with valid command name shows detailed help."""
    result = runner.invoke(app, ["help", "version"])
    assert result.exit_code == 0
    assert "version" in result.stdout.lower()
    assert "rentl version" in result.stdout


def test_help_command_with_invalid_command() -> None:
    """Test help command with invalid command name shows error and valid commands."""
    result = runner.invoke(app, ["help", "badcommand"])
    assert result.exit_code == ExitCode.VALIDATION_ERROR.value
    assert "Invalid command" in result.stdout or "badcommand" in result.stdout
    assert "version" in result.stdout  # Should list valid commands


def test_doctor_command_missing_config() -> None:
    """Test doctor command with missing config file."""
    result = runner.invoke(app, ["doctor", "--config", "/nonexistent/rentl.toml"])
    # Doctor should handle missing config gracefully
    assert result.exit_code != 0
    # Output should be present (either table or error message)
    assert len(result.stdout) > 0


def test_doctor_command_with_valid_config(tmp_path: Path) -> None:
    """Test doctor command with valid config runs diagnostics."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)

    # Create workspace directories
    (workspace_dir / ".rentl").mkdir()
    (workspace_dir / "logs").mkdir()

    result = runner.invoke(app, ["doctor", "--config", str(config_path)])
    # Exit code depends on checks, but should complete
    assert result.exit_code in [
        0,
        ExitCode.CONFIG_ERROR.value,
        ExitCode.CONNECTION_ERROR.value,
    ]
    # Should contain check results
    assert "Python Version" in result.stdout or "python" in result.stdout.lower()


def test_explain_command_no_args() -> None:
    """Test explain command without arguments lists all phases."""
    result = runner.invoke(app, ["explain"])
    assert result.exit_code == 0
    # Should list all 7 phases
    assert "ingest" in result.stdout.lower()
    assert "translate" in result.stdout.lower()
    assert "export" in result.stdout.lower()


def test_explain_command_with_valid_phase() -> None:
    """Test explain command with valid phase name shows phase details."""
    result = runner.invoke(app, ["explain", "ingest"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout.lower()
    # Should contain phase information sections
    assert (
        "Input" in result.stdout
        or "Output" in result.stdout
        or "Description" in result.stdout
    )


def test_explain_command_with_invalid_phase() -> None:
    """Test explain command with invalid phase name shows error and valid phases."""
    result = runner.invoke(app, ["explain", "badphase"])
    assert result.exit_code == ExitCode.VALIDATION_ERROR.value
    assert "Invalid phase" in result.stdout or "badphase" in result.stdout
    assert "ingest" in result.stdout  # Should list valid phases


def test_help_command_tty_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test help command Rich rendering paths by forcing Console terminal mode.

    Note: CliRunner cannot truly emulate TTY behavior because it replaces stdout
    with a capture buffer. This test validates the Rich rendering code paths execute
    without errors by forcing Console to emit ANSI codes and patching isatty.
    """
    from rich.console import Console as RichConsole  # noqa: PLC0415

    # Capture whether Console was created with the expected terminal settings
    console_configs: list[dict] = []

    # Patch Console in the CLI module to force terminal mode and capture config
    class PatchedConsole(RichConsole):
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            # Force terminal mode to emit ANSI codes
            kwargs["force_terminal"] = True
            console_configs.append(kwargs.copy())
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(cli_main, "Console", PatchedConsole)
    # Patch isatty to return True, triggering the Rich code paths
    monkeypatch.setattr("rentl_cli.main.sys.stdout.isatty", lambda: True)

    # Test list all commands (Rich table path)
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0
    # Verify Console was created with terminal mode forced
    assert len(console_configs) >= 1
    assert console_configs[0]["force_terminal"] is True
    # Verify output contains command names (validates execution path)
    assert "version" in result.stdout
    assert "doctor" in result.stdout

    # Reset console_configs for next test
    console_configs.clear()

    # Test specific command (Rich panel path)
    result = runner.invoke(app, ["help", "version"])
    assert result.exit_code == 0
    # Verify Console was created with terminal mode forced
    assert len(console_configs) >= 1
    assert console_configs[0]["force_terminal"] is True
    # Verify output contains version info (validates execution path)
    assert "version" in result.stdout.lower()


def test_explain_command_tty_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test explain command Rich rendering paths by forcing Console terminal mode.

    Note: CliRunner cannot truly emulate TTY behavior because it replaces stdout
    with a capture buffer. This test validates the Rich rendering code paths execute
    without errors by forcing Console to emit ANSI codes and patching isatty.
    """
    from rich.console import Console as RichConsole  # noqa: PLC0415

    # Capture whether Console was created with the expected terminal settings
    console_configs: list[dict] = []

    # Patch Console in the CLI module to force terminal mode and capture config
    class PatchedConsole(RichConsole):
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            # Force terminal mode to emit ANSI codes
            kwargs["force_terminal"] = True
            console_configs.append(kwargs.copy())
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(cli_main, "Console", PatchedConsole)
    # Patch isatty to return True, triggering the Rich code paths
    monkeypatch.setattr("rentl_cli.main.sys.stdout.isatty", lambda: True)

    # Test list all phases (Rich table path)
    result = runner.invoke(app, ["explain"])
    assert result.exit_code == 0
    # Verify Console was created with terminal mode forced
    assert len(console_configs) >= 1
    assert console_configs[0]["force_terminal"] is True
    # Verify output contains phase names (validates execution path)
    assert "ingest" in result.stdout.lower()
    assert "translate" in result.stdout.lower()

    # Reset console_configs for next test
    console_configs.clear()

    # Test specific phase (Rich panel path)
    result = runner.invoke(app, ["explain", "ingest"])
    assert result.exit_code == 0
    # Verify Console was created with terminal mode forced
    assert len(console_configs) >= 1
    assert console_configs[0]["force_terminal"] is True
    # Verify output contains phase info (validates execution path)
    assert "ingest" in result.stdout.lower()
    # Should contain phase information sections
    assert "Input" in result.stdout or "Output" in result.stdout


def test_doctor_command_tty_rendering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test doctor command Rich rendering paths by forcing Console terminal mode.

    Note: CliRunner cannot truly emulate TTY behavior because it replaces stdout
    with a capture buffer. This test validates the Rich rendering code paths execute
    without errors by forcing Console to emit ANSI codes and patching isatty.
    """
    from rich.console import Console as RichConsole  # noqa: PLC0415

    # Capture whether Console was created with the expected terminal settings
    console_configs: list[dict] = []

    # Patch Console in the CLI module to force terminal mode and capture config
    class PatchedConsole(RichConsole):
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            # Force terminal mode to emit ANSI codes
            kwargs["force_terminal"] = True
            console_configs.append(kwargs.copy())
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(cli_main, "Console", PatchedConsole)
    # Patch isatty to return True, triggering the Rich code paths
    monkeypatch.setattr("rentl_cli.main.sys.stdout.isatty", lambda: True)

    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)

    # Create workspace directories
    (workspace_dir / ".rentl").mkdir()
    (workspace_dir / "logs").mkdir()

    # Run doctor with Rich rendering
    result = runner.invoke(app, ["doctor", "--config", str(config_path)])

    # Verify Console was created with terminal mode forced
    assert len(console_configs) >= 1
    assert console_configs[0]["force_terminal"] is True
    # Verify output contains check results (validates execution path)
    assert "Python Version" in result.stdout or "python" in result.stdout.lower()
    assert "Overall" in result.stdout  # Overall status line


def test_doctor_command_exit_propagation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test that doctor propagates non-success exit codes when checks fail.

    This test validates the exit code propagation logic at
    services/rentl-cli/src/rentl_cli/main.py:374
    by ensuring that failing checks result in non-zero exit codes.
    """
    from rich.console import Console as RichConsole  # noqa: PLC0415

    # Patch Console in the CLI module to force terminal mode
    class PatchedConsole(RichConsole):
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            kwargs["force_terminal"] = True
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(cli_main, "Console", PatchedConsole)
    # Patch isatty to return True, triggering the Rich code paths
    monkeypatch.setattr("rentl_cli.main.sys.stdout.isatty", lambda: True)

    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)

    # Intentionally omit workspace directories to trigger failures
    # (don't create .rentl and logs directories)

    # Run doctor - should fail workspace check
    result = runner.invoke(app, ["doctor", "--config", str(config_path)])

    # Verify non-success exit code propagates (main.py:374-375)
    assert result.exit_code != 0, (
        "Doctor should return non-zero exit code when checks fail"
    )
    assert result.exit_code in [
        ExitCode.CONFIG_ERROR.value,
        ExitCode.CONNECTION_ERROR.value,
    ], f"Expected CONFIG_ERROR or CONNECTION_ERROR, got {result.exit_code}"
    # Verify the failure is visible in output
    assert "fail" in result.stdout.lower() or "✗" in result.stdout, (
        "Failure should be visible in output"
    )


def test_help_command_plain_text_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test help command produces plain text when piped (non-TTY).

    Validates that Rich formatting degrades gracefully when output is piped,
    ensuring all commands produce readable plain text for scripting/logging.
    """
    # Force non-TTY mode (CliRunner does this by default, but be explicit)
    monkeypatch.setattr("rentl_cli.main.sys.stdout.isatty", lambda: False)

    # Test list all commands (plain text path)
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0
    # Should not contain ANSI escape codes (no color/formatting)
    assert "\x1b[" not in result.stdout, (
        "Plain text output should not contain ANSI codes"
    )
    # Should contain command names as plain text
    assert "version" in result.stdout
    assert "doctor" in result.stdout
    assert "help" in result.stdout

    # Test specific command (plain text path)
    result = runner.invoke(app, ["help", "version"])
    assert result.exit_code == 0
    # Should not contain ANSI escape codes
    assert "\x1b[" not in result.stdout, (
        "Plain text output should not contain ANSI codes"
    )
    # Should contain version info as plain text
    assert "version" in result.stdout.lower()


def test_doctor_command_plain_text_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test doctor command produces plain text when piped (non-TTY).

    Validates that Rich table degrades gracefully when output is piped,
    ensuring check results are readable in plain text for scripting/logging.
    """
    # Force non-TTY mode
    monkeypatch.setattr("rentl_cli.main.sys.stdout.isatty", lambda: False)

    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    config_path = _write_config(tmp_path, workspace_dir)

    # Create workspace directories
    (workspace_dir / ".rentl").mkdir()
    (workspace_dir / "logs").mkdir()

    result = runner.invoke(app, ["doctor", "--config", str(config_path)])

    # Should not contain ANSI escape codes (no color/box drawing)
    assert "\x1b[" not in result.stdout, (
        "Plain text output should not contain ANSI codes"
    )
    # Should contain check results as plain text
    assert "Python Version" in result.stdout or "python" in result.stdout.lower()
    # Should contain status indicators
    assert "pass" in result.stdout.lower() or "fail" in result.stdout.lower()


def test_explain_command_plain_text_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test explain command produces plain text when piped (non-TTY).

    Validates that Rich formatting degrades gracefully when output is piped,
    ensuring phase information is readable in plain text for scripting/logging.
    """
    # Force non-TTY mode
    monkeypatch.setattr("rentl_cli.main.sys.stdout.isatty", lambda: False)

    # Test list all phases (plain text path)
    result = runner.invoke(app, ["explain"])
    assert result.exit_code == 0
    # Should not contain ANSI escape codes
    assert "\x1b[" not in result.stdout, (
        "Plain text output should not contain ANSI codes"
    )
    # Should contain phase names as plain text
    assert "ingest" in result.stdout.lower()
    assert "translate" in result.stdout.lower()

    # Test specific phase (plain text path)
    result = runner.invoke(app, ["explain", "ingest"])
    assert result.exit_code == 0
    # Should not contain ANSI escape codes
    assert "\x1b[" not in result.stdout, (
        "Plain text output should not contain ANSI codes"
    )
    # Should contain phase info as plain text
    assert "ingest" in result.stdout.lower()
    assert "Input" in result.stdout or "Output" in result.stdout


def test_redaction_in_command_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the redactor is properly bootstrapped and wired into CLI commands.

    This test verifies that:
    1. The redactor is built from the config at CLI startup
    2. It's passed through to the log sink and artifact storage
    3. Debug logs are emitted when redaction occurs

    We test this by creating a log entry with a secret via the storage layer,
    since actual CLI commands don't typically log secrets in their normal flow.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    logs_dir = workspace / "logs"
    logs_dir.mkdir()

    # Set a secret API key in the environment
    test_secret = "sk-test-secret-12345678901234567890"
    monkeypatch.setenv("TEST_KEY", test_secret)

    # Build the redactor as the CLI would
    config = RedactionConfig(patterns=DEFAULT_PATTERNS, env_var_names=["TEST_KEY"])
    redactor = build_redactor(config, {"TEST_KEY": test_secret})

    # Create a log sink with redaction (as CLI commands do)
    log_store: LogStoreProtocol = FileSystemLogStore(str(logs_dir))
    storage_sink = StorageLogSink(log_store)
    redacting_sink = RedactingLogSink(storage_sink, redactor)

    # Emit a log entry that contains the secret
    run_id = uuid7()
    entry = LogEntry(
        timestamp="2026-02-09T12:00:00Z",
        level=LogLevel.INFO,
        event="test_event",
        run_id=run_id,
        phase=None,
        message=f"Using API key {test_secret}",
        data={"key": test_secret},
    )

    asyncio.run(redacting_sink.emit_log(entry))

    # Read the log file and verify redaction
    log_files = list(logs_dir.glob("*.jsonl"))
    assert len(log_files) > 0, "No log files created"

    content = log_files[0].read_text()
    assert test_secret not in content, "Secret value found in log - redaction failed"
    assert "[REDACTED]" in content, "Redacted placeholder not found"

    # Verify debug log was emitted
    assert '"event":"redaction_applied"' in content, (
        "No redaction_applied debug event found"
    )


def test_dict_to_toml_simple_values() -> None:
    """Test TOML serialization of simple values."""
    data = {
        "project": {
            "project_name": "test",
            "enabled": True,
            "count": 42,
            "ratio": math.pi,
        }
    }

    result = cli_main._dict_to_toml(data)

    # Parse the result back to verify it's valid TOML
    parsed = tomllib.loads(result)
    assert parsed["project"]["project_name"] == "test"
    assert parsed["project"]["enabled"] is True
    assert parsed["project"]["count"] == 42
    assert parsed["project"]["ratio"] == math.pi


def test_dict_to_toml_nested_tables() -> None:
    """Test TOML serialization of nested tables."""
    data = {
        "project": {
            "schema_version": {"major": 0, "minor": 1, "patch": 0},
            "project_name": "test",
        }
    }

    result = cli_main._dict_to_toml(data)

    # Parse the result back to verify it's valid TOML
    parsed = tomllib.loads(result)
    assert parsed["project"]["schema_version"]["major"] == 0
    assert parsed["project"]["schema_version"]["minor"] == 1
    assert parsed["project"]["schema_version"]["patch"] == 0


def test_dict_to_toml_arrays() -> None:
    """Test TOML serialization of arrays."""
    data = {
        "project": {"target_languages": ["en", "fr", "de"]},
        "logging": {"sinks": [{"type": "console"}, {"type": "file"}]},
    }

    result = cli_main._dict_to_toml(data)

    # Parse the result back to verify it's valid TOML
    parsed = tomllib.loads(result)
    assert parsed["project"]["target_languages"] == ["en", "fr", "de"]
    assert len(parsed["logging"]["sinks"]) == 2
    assert parsed["logging"]["sinks"][0]["type"] == "console"


def test_dict_to_toml_escaping() -> None:
    """Test TOML serialization handles escaping correctly."""
    data = {"test": {"value": 'quote" and backslash\\ here'}}

    result = cli_main._dict_to_toml(data)

    # Parse the result back to verify escaping worked
    parsed = tomllib.loads(result)
    assert parsed["test"]["value"] == 'quote" and backslash\\ here'


def test_auto_migrate_if_needed_up_to_date(tmp_path: Path) -> None:
    """Test auto-migrate skips migration when config is already up to date."""
    config_path = tmp_path / "rentl.toml"
    payload = {
        "project": {
            "schema_version": {"major": 0, "minor": 1, "patch": 0},
            "project_name": "test",
        }
    }

    result = cli_main._auto_migrate_if_needed(config_path, payload)

    # Should return the same payload unchanged
    assert result == payload
    # Should not create a backup
    assert not (config_path.with_suffix(".toml.bak")).exists()


def test_auto_migrate_if_needed_outdated(tmp_path: Path) -> None:
    """Test auto-migrate upgrades outdated config and creates backup."""
    config_path = tmp_path / "rentl.toml"

    # Write an old config
    old_config_content = """[project]
schema_version = { major = 0, minor = 0, patch = 1 }
project_name = "test-project"

[project.paths]
workspace_dir = "."
input_path = "./input/test.jsonl"
output_dir = "./out"
logs_dir = "./logs"

[project.formats]
input_format = "jsonl"
output_format = "jsonl"

[project.languages]
source_language = "ja"
target_languages = ["en"]

[logging]
sinks = [
    { type = "console" },
]

[endpoint]
provider_name = "test"
base_url = "http://localhost"
api_key_env = "TEST_API_KEY"
model_id = "test-model"
"""
    config_path.write_text(old_config_content, encoding="utf-8")

    # Load the old config
    with config_path.open("rb") as f:
        payload = tomllib.load(f)

    # Run auto-migrate
    result = cli_main._auto_migrate_if_needed(config_path, payload)

    # Should have upgraded the schema version
    project = cast(dict, result["project"])
    schema_version = cast(dict, project["schema_version"])
    assert schema_version["major"] == 0
    assert schema_version["minor"] == 1
    assert schema_version["patch"] == 0

    # Should have created a backup
    backup_path = config_path.with_suffix(".toml.bak")
    assert backup_path.exists()

    # Backup should contain the original version
    with backup_path.open("rb") as f:
        backup = tomllib.load(f)
    backup_project = cast(dict, backup["project"])
    backup_schema_version = cast(dict, backup_project["schema_version"])
    assert backup_schema_version["major"] == 0
    assert backup_schema_version["minor"] == 0
    assert backup_schema_version["patch"] == 1

    # Config file should have been updated
    with config_path.open("rb") as f:
        updated = tomllib.load(f)
    updated_project = cast(dict, updated["project"])
    updated_schema_version = cast(dict, updated_project["schema_version"])
    assert updated_schema_version["major"] == 0
    assert updated_schema_version["minor"] == 1
    assert updated_schema_version["patch"] == 0


def test_auto_migrate_if_needed_no_schema_version(tmp_path: Path) -> None:
    """Test auto-migrate skips migration when no schema_version field exists."""
    config_path = tmp_path / "rentl.toml"
    payload = {"project": {"project_name": "test"}}

    result = cli_main._auto_migrate_if_needed(config_path, payload)

    # Should return the same payload unchanged
    assert result == payload
    # Should not create a backup
    assert not (config_path.with_suffix(".toml.bak")).exists()


def test_load_dotenv_loads_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that _load_dotenv loads .env file from config directory."""
    config_path = tmp_path / "rentl.toml"
    config_path.write_text("[project]\n", encoding="utf-8")

    # Create .env file with a test key
    env_path = tmp_path / ".env"
    env_path.write_text("TEST_ENV_KEY=value_from_env\n", encoding="utf-8")

    # Clear the environment to ensure we're testing .env loading
    monkeypatch.delenv("TEST_ENV_KEY", raising=False)

    # Load dotenv
    cli_main._load_dotenv(config_path)

    # Verify the key was loaded from .env
    assert os.getenv("TEST_ENV_KEY") == "value_from_env"


def test_load_dotenv_loads_env_local_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that _load_dotenv loads .env.local file from config directory."""
    config_path = tmp_path / "rentl.toml"
    config_path.write_text("[project]\n", encoding="utf-8")

    # Create .env.local file with a test key
    env_local_path = tmp_path / ".env.local"
    env_local_path.write_text("TEST_LOCAL_KEY=value_from_local\n", encoding="utf-8")

    # Clear the environment to ensure we're testing .env.local loading
    monkeypatch.delenv("TEST_LOCAL_KEY", raising=False)

    # Load dotenv
    cli_main._load_dotenv(config_path)

    # Verify the key was loaded from .env.local
    assert os.getenv("TEST_LOCAL_KEY") == "value_from_local"


def test_load_dotenv_both_env_and_env_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that _load_dotenv loads both .env and .env.local files.

    Note: Currently .env takes precedence when both files define the same key
    (both are loaded with override=False, so first loaded wins).
    This is the actual behavior, though the docstring claims .env.local should
    take precedence.
    """
    config_path = tmp_path / "rentl.toml"
    config_path.write_text("[project]\n", encoding="utf-8")

    # Create .env file with keys
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SHARED_KEY=value_from_env\nENV_ONLY_KEY=env_value\n", encoding="utf-8"
    )

    # Create .env.local file with keys
    env_local_path = tmp_path / ".env.local"
    env_local_path.write_text(
        "SHARED_KEY=value_from_local\nLOCAL_ONLY_KEY=local_value\n", encoding="utf-8"
    )

    # Clear the environment to ensure we're testing .env loading
    monkeypatch.delenv("SHARED_KEY", raising=False)
    monkeypatch.delenv("ENV_ONLY_KEY", raising=False)
    monkeypatch.delenv("LOCAL_ONLY_KEY", raising=False)

    # Load dotenv
    cli_main._load_dotenv(config_path)

    # Verify both files are loaded
    assert os.getenv("ENV_ONLY_KEY") == "env_value"
    assert os.getenv("LOCAL_ONLY_KEY") == "local_value"
    # .env takes precedence (loaded first with override=False)
    assert os.getenv("SHARED_KEY") == "value_from_env"


def test_load_dotenv_handles_missing_env_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that _load_dotenv handles missing .env files gracefully."""
    config_path = tmp_path / "rentl.toml"
    config_path.write_text("[project]\n", encoding="utf-8")

    # Ensure no .env files exist
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / ".env.local").exists()

    # Should not raise an exception
    cli_main._load_dotenv(config_path)
