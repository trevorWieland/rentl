"""BDD integration tests for doctor CLI command."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

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

    # Create necessary workspace directories
    (tmp_workspace / "input").mkdir(exist_ok=True)
    (tmp_workspace / "out").mkdir(exist_ok=True)
    (tmp_workspace / "logs").mkdir(exist_ok=True)
    (tmp_workspace / "prompts").mkdir(exist_ok=True)
    (tmp_workspace / "agents").mkdir(exist_ok=True)

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
