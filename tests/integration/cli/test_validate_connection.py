"""Integration tests for validate-connection CLI command."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_schemas.llm import LlmPromptRequest, LlmPromptResponse

runner = CliRunner()


class _FakeRuntime:
    async def run_prompt(
        self, request: LlmPromptRequest, *, api_key: str
    ) -> LlmPromptResponse:
        return LlmPromptResponse(
            model_id=request.runtime.model.model_id,
            output_text="ok",
        )


def test_validate_connection_returns_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Given configured endpoints, when validating, then results are returned."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    input_path = workspace_dir / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    config_path = _write_connection_config(tmp_path, workspace_dir)

    monkeypatch.setenv("PRIMARY_KEY", "fake-key")
    monkeypatch.setenv("SECONDARY_KEY", "fake-key")
    monkeypatch.setenv("TERTIARY_KEY", "fake-key")
    monkeypatch.setattr(cli_main, "_build_llm_runtime", lambda: _FakeRuntime())

    result = runner.invoke(
        cli_main.app, ["validate-connection", "--config", str(config_path)]
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["error"] is None
    assert response["data"]["success_count"] == 2
    assert response["data"]["failure_count"] == 0
    assert response["data"]["skipped_count"] == 1


def _write_connection_config(tmp_path: Path, workspace_dir: Path) -> Path:
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

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "http://localhost:8001/v1"
        api_key_env = "PRIMARY_KEY"

        [[endpoints.endpoints]]
        provider_name = "secondary"
        base_url = "http://localhost:8002/v1"
        api_key_env = "SECONDARY_KEY"

        [[endpoints.endpoints]]
        provider_name = "tertiary"
        base_url = "http://localhost:8003/v1"
        api_key_env = "TERTIARY_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"
        endpoint_ref = "primary"

        [[pipeline.phases]]
        phase = "ingest"

        [[pipeline.phases]]
        phase = "context"

        [[pipeline.phases]]
        phase = "pretranslation"

        [[pipeline.phases]]
        phase = "translate"

        [pipeline.phases.model]
        model_id = "gpt-4"
        endpoint_ref = "secondary"

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
