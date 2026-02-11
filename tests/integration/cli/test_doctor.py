"""BDD integration tests for doctor CLI command."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from tests.integration.conftest import write_rentl_config

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/cli/doctor.feature")


class DoctorContext:
    """Context object for doctor BDD scenarios."""

    result: Result | None = None
    stdout: str = ""
    config_dir: Path | None = None


@given("a valid rentl configuration exists", target_fixture="ctx")
def given_valid_config(
    tmp_workspace: Path, set_api_keys: None, mock_llm_runtime: object
) -> DoctorContext:
    """Create a valid rentl configuration.

    Returns:
        DoctorContext with config directory.
    """
    ctx = DoctorContext()
    ctx.config_dir = tmp_workspace.parent
    write_rentl_config(ctx.config_dir, tmp_workspace)

    # Create necessary workspace directories inside tmp_workspace
    (tmp_workspace / "input").mkdir(exist_ok=True)
    (tmp_workspace / "prompts").mkdir(exist_ok=True)
    (tmp_workspace / "agents").mkdir(exist_ok=True)

    # Create output/logs directories relative to config directory (not workspace)
    # These are resolved as config_dir / "out" and config_dir / "logs" in doctor
    (ctx.config_dir / "out").mkdir(exist_ok=True)
    (ctx.config_dir / "logs").mkdir(exist_ok=True)

    return ctx


@given("no rentl configuration exists", target_fixture="ctx")
def given_no_config(tmp_path: Path) -> DoctorContext:
    """Create a directory with no rentl configuration.

    Returns:
        DoctorContext with empty config directory.
    """
    ctx = DoctorContext()
    ctx.config_dir = tmp_path
    return ctx


@when("I run the doctor command")
def when_run_doctor(ctx: DoctorContext, cli_runner: CliRunner) -> None:
    """Run the doctor CLI command.

    Args:
        ctx: Doctor context with config directory.
        cli_runner: CLI test runner.
    """
    # Change to config directory for the command
    assert ctx.config_dir is not None
    config_path = ctx.config_dir / "rentl.toml"
    ctx.result = cli_runner.invoke(
        cli_main.app, ["doctor", "--config", str(config_path)]
    )
    ctx.stdout = ctx.result.stdout


@then("the output contains check results")
def then_output_contains_check_results(ctx: DoctorContext) -> None:
    """Assert the output contains check results."""
    # Should contain at least one check name
    assert (
        "python" in ctx.stdout.lower()
        or "config" in ctx.stdout.lower()
        or "workspace" in ctx.stdout.lower()
    )


@then("the output contains config error details")
def then_output_contains_config_error(ctx: DoctorContext) -> None:
    """Assert the output contains config error details."""
    assert "config" in ctx.stdout.lower()
    assert "fail" in ctx.stdout.lower() or "error" in ctx.stdout.lower()


@then("the output contains actionable fix suggestions")
def then_output_contains_fix_suggestions(ctx: DoctorContext) -> None:
    """Assert the output contains actionable fix suggestions."""
    # Should contain actionable text like "run", "create", "set", etc.
    assert any(
        keyword in ctx.stdout.lower()
        for keyword in ["run", "create", "set", "install", "configure"]
    )


@given("API keys are set in .env file")
def given_api_keys_in_env_file(
    ctx: DoctorContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Create a .env file with required API keys.

    Args:
        ctx: Doctor context with config directory.
        monkeypatch: Pytest monkeypatch fixture.
    """
    assert ctx.config_dir is not None

    # Clear env vars to ensure we're testing .env loading
    monkeypatch.delenv("RENTL_OPENROUTER_API_KEY", raising=False)

    # Create .env file with API key
    env_path = ctx.config_dir / ".env"
    env_path.write_text("RENTL_OPENROUTER_API_KEY=test_key_from_dotenv\n")


@then("the API key check passes")
def then_api_key_check_passes(ctx: DoctorContext) -> None:
    """Assert the API key check passes."""
    assert ctx.result is not None
    assert ctx.result.exit_code == 0
    # Should show API key check passed (not failed)
    assert "api key" in ctx.stdout.lower() or "api" in ctx.stdout.lower()
