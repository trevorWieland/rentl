"""Unit tests for rentl-cli."""

import ast
import asyncio
import inspect
import json
import textwrap
from pathlib import Path
from typing import cast
from uuid import uuid7

import pytest
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_cli.main import app
from rentl_core.orchestrator import PipelineOrchestrator
from rentl_core.ports.orchestrator import LogSinkProtocol
from rentl_schemas.events import CommandEvent, ProgressEvent
from rentl_schemas.io import SourceLine
from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse
from rentl_schemas.logs import LogEntry
from rentl_schemas.phases import ContextPhaseOutput, SceneSummary
from rentl_schemas.pipeline import PhaseRunRecord, RunMetadata, RunState
from rentl_schemas.primitives import PhaseName, PhaseStatus, RunStatus
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


def test_run_pipeline_errors_when_agents_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run-pipeline returns config error when agents are missing."""
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

    run_id = uuid7()
    result = runner.invoke(
        app,
        ["run-pipeline", "--config", str(config_path), "--run-id", str(run_id)],
    )

    assert result.exit_code == 11  # ExitCode.VALIDATION_ERROR
    response = ApiResponse[RunExecutionResult].model_validate_json(result.stdout)
    assert response.error is not None
    assert response.error.code == "validation_error"
    assert response.error.exit_code == 11


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
                for keyword in node.keywords:
                    if (
                        keyword.arg == "code"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, int)
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
