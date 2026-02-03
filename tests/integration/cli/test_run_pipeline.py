"""BDD integration tests for run-pipeline CLI command."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from tests.integration.conftest import FakeLlmRuntime

if TYPE_CHECKING:
    import pytest
    from click.testing import Result

# Link feature file
scenarios("../features/cli/run_pipeline.feature")


def _write_pipeline_config(config_path: Path, workspace_dir: Path) -> Path:
    """Write a rentl.toml config for pipeline tests with only ingest enabled.

    Returns:
        Path to the written config file.
    """
    content = textwrap.dedent(
        f"""\
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
        source_language = "ja"
        target_languages = ["en"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "http://localhost:8001/v1"
        api_key_env = "PRIMARY_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"
        endpoint_ref = "primary"

        [[pipeline.phases]]
        phase = "ingest"
        enabled = true

        [[pipeline.phases]]
        phase = "context"
        enabled = false

        [[pipeline.phases]]
        phase = "pretranslation"
        enabled = false

        [[pipeline.phases]]
        phase = "translate"
        enabled = false

        [[pipeline.phases]]
        phase = "qa"
        enabled = false

        [[pipeline.phases]]
        phase = "edit"
        enabled = false

        [[pipeline.phases]]
        phase = "export"
        enabled = false

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
    )
    file_path = config_path / "rentl.toml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


class PipelineContext:
    """Context object for run-pipeline BDD scenarios."""

    config_path: Path | None = None
    workspace_dir: Path | None = None
    result: Result | None = None
    response: dict | None = None


@given("a rentl config with ingest phase enabled", target_fixture="ctx")
def given_config_ingest_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> PipelineContext:
    """Create a config with only ingest phase enabled.

    Returns:
        PipelineContext with workspace and config initialized.
    """
    ctx = PipelineContext()
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()
    ctx.config_path = _write_pipeline_config(tmp_path, ctx.workspace_dir)
    monkeypatch.setenv("PRIMARY_KEY", "fake-key")
    monkeypatch.setattr(cli_main, "_build_llm_runtime", lambda: FakeLlmRuntime())
    return ctx


@given("an input file with source lines")
def given_input_file(ctx: PipelineContext) -> None:
    """Create an input file with source lines."""
    assert ctx.workspace_dir is not None
    input_path = ctx.workspace_dir / "input.txt"
    input_path.write_text("こんにちは\nさようなら\n", encoding="utf-8")


@given("no input file exists")
def given_no_input_file(ctx: PipelineContext) -> None:
    """Ensure no input file exists."""
    assert ctx.workspace_dir is not None
    input_path = ctx.workspace_dir / "input.txt"
    if input_path.exists():
        input_path.unlink()


@when("I run the pipeline command")
def when_run_pipeline(ctx: PipelineContext, cli_runner: CliRunner) -> None:
    """Run the run-pipeline CLI command."""
    ctx.result = cli_runner.invoke(
        cli_main.app,
        ["run-pipeline", "--config", str(ctx.config_path)],
    )
    if ctx.result.stdout:
        ctx.response = json.loads(ctx.result.stdout)


@then("the response contains run data")
def then_response_contains_run_data(ctx: PipelineContext) -> None:
    """Assert the response contains run data."""
    assert ctx.response is not None
    assert ctx.response.get("error") is None, (
        f"Unexpected error: {ctx.response.get('error')}"
    )
    assert ctx.response.get("data") is not None
    assert ctx.response["data"].get("run_id") is not None
