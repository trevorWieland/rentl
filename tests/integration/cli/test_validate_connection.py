"""BDD integration tests for validate-connection CLI command."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main

if TYPE_CHECKING:
    from click.testing import Result

    from tests.integration.conftest import FakeLlmRuntime

# Link feature file
scenarios("../features/cli/validate_connection.feature")


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
    )
    file_path = config_path / "rentl.toml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


# --- Fixtures for BDD context ---


class ValidateConnectionContext:
    """Context object for validate-connection BDD scenarios."""

    config_path: Path | None = None
    result: Result | None = None
    response: dict | None = None


@given("a rentl config with multiple endpoints", target_fixture="ctx")
def given_config_with_endpoints(
    tmp_path: Path,
    tmp_workspace: Path,
) -> ValidateConnectionContext:
    """Create a rentl config with multiple endpoints.

    Returns:
        ValidateConnectionContext with config path initialized.
    """
    ctx = ValidateConnectionContext()
    # Create input file
    input_path = tmp_workspace / "input.txt"
    input_path.write_text("Hello\n", encoding="utf-8")
    ctx.config_path = _write_rentl_config(tmp_path, tmp_workspace)
    return ctx


@given("all required API keys are set in environment")
def given_api_keys_set(
    set_api_keys: None,
) -> None:
    """Set all required API keys in the environment."""


@given("no config file exists", target_fixture="ctx")
def given_no_config(tmp_path: Path) -> ValidateConnectionContext:
    """Ensure no config file exists.

    Returns:
        ValidateConnectionContext with nonexistent config path.
    """
    ctx = ValidateConnectionContext()
    ctx.config_path = tmp_path / "nonexistent" / "rentl.toml"
    return ctx


@when("I run the validate-connection command")
def when_run_validate_connection(
    ctx: ValidateConnectionContext,
    cli_runner: CliRunner,
    mock_llm_runtime: FakeLlmRuntime,
) -> None:
    """Run the validate-connection CLI command."""
    ctx.result = cli_runner.invoke(
        cli_main.app,
        ["validate-connection", "--config", str(ctx.config_path)],
    )
    if ctx.result.stdout:
        ctx.response = json.loads(ctx.result.stdout)


@when("I run the validate-connection command with the missing config")
def when_run_validate_connection_missing_config(
    ctx: ValidateConnectionContext,
    cli_runner: CliRunner,
) -> None:
    """Run the validate-connection CLI command with missing config."""
    ctx.result = cli_runner.invoke(
        cli_main.app,
        ["validate-connection", "--config", str(ctx.config_path)],
    )
    if ctx.result.stdout:
        ctx.response = json.loads(ctx.result.stdout)


@then("the command succeeds with an error response")
def then_command_succeeds_with_error(ctx: ValidateConnectionContext) -> None:
    """Assert the CLI exits 0 but returns an error response."""
    assert ctx.result is not None
    assert ctx.result.exit_code == 0
    assert ctx.response is not None
    assert ctx.response["error"] is not None


@then("the response shows successful validations")
def then_response_shows_successes(ctx: ValidateConnectionContext) -> None:
    """Assert the response contains successful validations."""
    assert ctx.response is not None
    assert ctx.response["error"] is None
    assert ctx.response["data"]["success_count"] == 2


@then("the response shows skipped endpoints")
def then_response_shows_skipped(ctx: ValidateConnectionContext) -> None:
    """Assert the response contains skipped endpoints."""
    assert ctx.response is not None
    assert ctx.response["data"]["skipped_count"] == 1
