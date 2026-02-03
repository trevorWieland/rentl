"""Unit tests for rentl-cli."""

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from rentl_cli.main import app

runner = CliRunner()


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

    result = runner.invoke(app, ["run-pipeline", "--config", str(config_path)])

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"]["code"] == "invalid_state"


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
