"""BDD integration tests for explain CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import Result
from pytest_bdd import scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/cli/explain.feature")


class ExplainContext:
    """Context object for explain BDD scenarios."""

    result: Result | None = None
    stdout: str = ""


@when("I run the explain command with no arguments", target_fixture="ctx")
def when_run_explain_no_args(cli_runner: CliRunner) -> ExplainContext:
    """Run the explain CLI command with no arguments.

    Returns:
        ExplainContext with command result.
    """
    ctx = ExplainContext()
    ctx.result = cli_runner.invoke(cli_main.app, ["explain"])
    ctx.stdout = ctx.result.stdout
    return ctx


@when('I run the explain command for phase "translate"', target_fixture="ctx")
def when_run_explain_translate(cli_runner: CliRunner) -> ExplainContext:
    """Run the explain CLI command for translate phase.

    Returns:
        ExplainContext with command result.
    """
    ctx = ExplainContext()
    ctx.result = cli_runner.invoke(cli_main.app, ["explain", "translate"])
    ctx.stdout = ctx.result.stdout
    return ctx


@when('I run the explain command for phase "badphase"', target_fixture="ctx")
def when_run_explain_badphase(cli_runner: CliRunner) -> ExplainContext:
    """Run the explain CLI command for invalid phase.

    Returns:
        ExplainContext with command result.
    """
    ctx = ExplainContext()
    ctx.result = cli_runner.invoke(cli_main.app, ["explain", "badphase"])
    ctx.stdout = ctx.result.stdout
    return ctx


@then("the output contains all phase names")
def then_output_contains_phase_names(ctx: ExplainContext) -> None:
    """Assert the output contains phase names."""
    # Check for a few known phases
    assert "ingest" in ctx.stdout.lower()
    assert "translate" in ctx.stdout.lower()
    assert "export" in ctx.stdout.lower()


@then("the output contains detailed phase information")
def then_output_contains_detailed_phase_info(ctx: ExplainContext) -> None:
    """Assert the output contains detailed phase information."""
    assert "translate" in ctx.stdout.lower()
    # Should contain section headers for detailed info
    assert any(
        keyword in ctx.stdout.lower()
        for keyword in ["input", "output", "prerequisite", "config"]
    )


@then("the output contains valid phase names")
def then_output_contains_valid_phases(ctx: ExplainContext) -> None:
    """Assert the output contains valid phase names list."""
    # Should mention valid phases in error message
    assert "ingest" in ctx.stdout.lower() or "translate" in ctx.stdout.lower()


@then("the output contains helpful error with phase list")
def then_output_contains_helpful_error(ctx: ExplainContext) -> None:
    """Assert the output contains a helpful error with valid phase list."""
    # Should have both error indication and valid phase list
    assert "invalid" in ctx.stdout.lower() or "error" in ctx.stdout.lower()
    # Should list at least a few valid phases
    assert "ingest" in ctx.stdout.lower()
    assert "translate" in ctx.stdout.lower()
