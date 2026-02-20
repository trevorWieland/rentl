"""BDD integration tests for CLI exit codes."""

from __future__ import annotations

import contextlib
import json
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import Result
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/cli/exit_codes.feature")


def _write_rentl_config(config_path: Path, workspace_dir: Path) -> Path:
    """Write a rentl.toml config file for testing.

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

        [agents]
        prompts_dir = "{workspace_dir}/prompts"
        agents_dir = "{workspace_dir}/agents"

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
        agents = ["context_agent"]

        [[pipeline.phases]]
        phase = "pretranslation"
        enabled = false
        agents = ["pretranslation_agent"]

        [[pipeline.phases]]
        phase = "translate"
        enabled = false
        agents = ["translate_agent"]

        [[pipeline.phases]]
        phase = "qa"
        enabled = false
        agents = ["qa_agent"]

        [[pipeline.phases]]
        phase = "edit"
        enabled = false
        agents = ["edit_agent"]

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


# --- Fixtures for BDD context ---


class ExitCodeContext:
    """Context object for exit code BDD scenarios."""

    config_path: Path | None = None
    workspace_dir: Path | None = None
    result: Result | None = None
    response: dict | None = None


@given("no config file exists", target_fixture="ctx")
def given_no_config(tmp_path: Path) -> ExitCodeContext:
    """Ensure no config file exists.

    Returns:
        ExitCodeContext with nonexistent config path.
    """
    ctx = ExitCodeContext()
    ctx.config_path = tmp_path / "nonexistent" / "rentl.toml"
    return ctx


@given("a rentl config with valid settings", target_fixture="ctx")
def given_valid_config(
    tmp_path: Path,
    tmp_workspace: Path,
) -> ExitCodeContext:
    """Create a rentl config with valid settings.

    Returns:
        ExitCodeContext with config path initialized.
    """
    ctx = ExitCodeContext()
    ctx.workspace_dir = tmp_workspace
    # Create input file
    input_path = tmp_workspace / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    ctx.config_path = _write_rentl_config(tmp_path, tmp_workspace)
    return ctx


@when("I run the version command", target_fixture="ctx")
def when_run_version(cli_runner: CliRunner) -> ExitCodeContext:
    """Run the version CLI command.

    Returns:
        ExitCodeContext with command result.
    """
    ctx = ExitCodeContext()
    ctx.result = cli_runner.invoke(cli_main.app, ["version"])
    return ctx


@when("I run run-pipeline with the missing config")
def when_run_pipeline_missing_config(
    ctx: ExitCodeContext,
    cli_runner: CliRunner,
) -> None:
    """Run the run-pipeline CLI command with missing config."""
    ctx.result = cli_runner.invoke(
        cli_main.app,
        ["run-pipeline", "--config", str(ctx.config_path)],
    )
    if ctx.result.stdout:
        # If stdout is not JSON, leave response as None
        with contextlib.suppress(json.JSONDecodeError):
            ctx.response = json.loads(ctx.result.stdout)


@when("I run run-pipeline with the missing config in JSON mode")
def when_run_pipeline_missing_config_json(
    ctx: ExitCodeContext,
    cli_runner: CliRunner,
) -> None:
    """Run the run-pipeline CLI command with missing config in JSON mode."""
    ctx.result = cli_runner.invoke(
        cli_main.app,
        ["run-pipeline", "--config", str(ctx.config_path)],
    )
    if ctx.result.stdout:
        # If stdout is not JSON, leave response as None
        with contextlib.suppress(json.JSONDecodeError):
            ctx.response = json.loads(ctx.result.stdout)


@when("I run export with an invalid run ID")
def when_run_export_invalid_id(
    ctx: ExitCodeContext,
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Run the export CLI command with parameters that trigger a ValueError.

    We use expected-line-count to trigger a validation error when the actual
    line count doesn't match the expected count.
    """
    monkeypatch.setenv("PRIMARY_KEY", "fake-key")

    # Create input file with 2 lines
    input_file = tmp_path / "input.jsonl"
    input_file.write_text(
        '{"scene_id": "1", "line_id": "1", "text": "test", "speaker": null}\n'
        '{"scene_id": "1", "line_id": "2", "text": "test2", "speaker": null}\n'
    )
    output_file = tmp_path / "output.csv"

    # Use expected-line-count that doesn't match actual count (2 vs 999)
    # This should trigger a ValueError in the export logic
    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "export",
            "--config",
            str(ctx.config_path),
            "--input",
            str(input_file),
            "--output",
            str(output_file),
            "--format",
            "csv",
            "--expected-line-count",
            "999",
        ],
    )
    if ctx.result.stdout:
        with contextlib.suppress(json.JSONDecodeError):
            ctx.response = json.loads(ctx.result.stdout)


@when("I trigger a runtime error in the CLI")
def when_trigger_runtime_error(
    ctx: ExitCodeContext,
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Trigger a runtime error in the CLI by causing an unexpected exception.

    We monkeypatch write_output to raise a KeyError (unexpected runtime error)
    that will be caught by the generic Exception handler and mapped to exit 99.
    """
    monkeypatch.setenv("PRIMARY_KEY", "fake-key")

    # Monkeypatch _export_async to raise an unexpected KeyError
    # This will bypass all the normal error handling paths and trigger exit 99
    export_called = {"count": 0}

    async def raise_runtime_error(  # noqa: RUF029
        *args: str | Path, **kwargs: str | int | bool
    ) -> None:
        export_called["count"] += 1
        raise KeyError("Simulated runtime error for testing exit code 99")

    monkeypatch.setattr(cli_main, "_export_async", raise_runtime_error)

    # Create valid input file
    input_file = tmp_path / "input.jsonl"
    input_file.write_text(
        '{"scene_id": "1", "line_id": "1", "text": "test", "speaker": null}\n'
    )
    output_file = tmp_path / "output.csv"

    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "export",
            "--config",
            str(ctx.config_path),
            "--input",
            str(input_file),
            "--output",
            str(output_file),
            "--format",
            "csv",
        ],
    )
    if ctx.result.stdout:
        with contextlib.suppress(json.JSONDecodeError):
            ctx.response = json.loads(ctx.result.stdout)

    # Assert the patched _export_async was actually invoked
    assert export_called["count"] > 0, (
        "_export_async mock was never called — the monkeypatch may not be targeting "
        "the correct attribute"
    )


@then("the command succeeds")
def then_command_succeeds(ctx: ExitCodeContext) -> None:
    """Assert the CLI command exits with code 0."""
    assert ctx.result is not None
    assert ctx.result.exit_code == 0, (
        f"Expected exit code 0, got {ctx.result.exit_code}: {ctx.result.stdout}"
    )


@then("the command returns an error response")
def then_command_returns_error(ctx: ExitCodeContext) -> None:
    """Assert the command returns an error response with non-zero exit code."""
    assert ctx.result is not None
    assert ctx.result.exit_code != 0  # CLI must exit with non-zero code on error
    assert ctx.response is not None, f"Expected JSON response, got: {ctx.result.stdout}"
    assert ctx.response.get("error") is not None, (
        f"Expected error in response, got: {ctx.response}"
    )
    # Verify exit code in response matches the CLI exit code
    assert ctx.response["error"]["exit_code"] == ctx.result.exit_code, (
        f"Exit code mismatch: CLI={ctx.result.exit_code}, "
        f"JSON={ctx.response['error']['exit_code']}"
    )


@then(parsers.parse("the exit code is {expected_code:d}"))
def then_exit_code_is(ctx: ExitCodeContext, expected_code: int) -> None:
    """Assert the CLI exit code matches the expected value."""
    assert ctx.result is not None
    assert ctx.result.exit_code == expected_code, (
        f"Expected exit code {expected_code}, got {ctx.result.exit_code}"
    )


@then(parsers.parse('the error code is "{error_code}"'))
def then_error_code_is(ctx: ExitCodeContext, error_code: str) -> None:
    """Assert the error response has the expected code."""
    assert ctx.response is not None
    assert ctx.response["error"] is not None
    assert ctx.response["error"]["code"] == error_code, (
        f"Expected error code '{error_code}', got '{ctx.response['error']['code']}'"
    )


@then(
    parsers.parse(
        "the JSON response includes exit_code field with value {expected_code:d}"
    )
)
def then_json_includes_exit_code(ctx: ExitCodeContext, expected_code: int) -> None:
    """Assert the JSON response includes the exit_code field with expected value."""
    assert ctx.response is not None
    assert ctx.response["error"] is not None
    assert "exit_code" in ctx.response["error"], (
        f"Expected exit_code in error response, got: {ctx.response['error']}"
    )
    assert ctx.response["error"]["exit_code"] == expected_code, (
        f"Expected exit_code {expected_code}, got {ctx.response['error']['exit_code']}"
    )
