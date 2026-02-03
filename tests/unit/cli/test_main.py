"""Unit tests for rentl-cli."""

import json
import textwrap
from pathlib import Path
from uuid import uuid7

import pytest
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_cli.main import app
from rentl_schemas.events import CommandEvent
from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse
from rentl_schemas.logs import LogEntry
from rentl_schemas.responses import ApiResponse, RunExecutionResult

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
    """Run-pipeline returns structured error when agents are missing."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    config_path = _write_config(tmp_path, workspace_dir)

    monkeypatch.setenv("TEST_KEY", "fake-key")

    run_id = uuid7()
    result = runner.invoke(
        app,
        ["run-pipeline", "--config", str(config_path), "--run-id", str(run_id)],
    )

    assert result.exit_code == 0
    response = ApiResponse[RunExecutionResult].model_validate_json(result.stdout)
    assert response.error is not None
    assert response.error.code == "invalid_state"
    log_path = workspace_dir / "logs" / f"{run_id}.jsonl"
    assert log_path.exists()
    events = _log_event_names(_read_log_entries(log_path))
    assert CommandEvent.STARTED.value in events
    assert CommandEvent.FAILED.value in events


def test_run_pipeline_returns_config_error(tmp_path: Path) -> None:
    """Invalid TOML config yields config_error response."""
    config_path = tmp_path / "rentl.toml"
    config_path.write_text("invalid = [", encoding="utf-8")

    result = runner.invoke(app, ["run-pipeline", "--config", str(config_path)])

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"]["code"] == "config_error"


def test_run_pipeline_errors_on_missing_endpoint_key(tmp_path: Path) -> None:
    """Missing API key env var returns config_error response."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    config_path = _write_multi_endpoint_config(tmp_path, workspace_dir)

    result = runner.invoke(app, ["run-pipeline", "--config", str(config_path)])

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"]["code"] == "config_error"
    assert "SECONDARY_KEY" in response["error"]["message"]


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

        [[pipeline.phases]]
        phase = "pretranslation"

        [[pipeline.phases]]
        phase = "translate"

        [[pipeline.phases]]
        phase = "qa"

        [[pipeline.phases]]
        phase = "edit"

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

        [[pipeline.phases]]
        phase = "pretranslation"

        [[pipeline.phases]]
        phase = "translate"

        [[pipeline.phases]]
        phase = "qa"

        [[pipeline.phases]]
        phase = "edit"

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
