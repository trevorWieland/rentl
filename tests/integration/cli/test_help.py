"""BDD integration tests for help CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import Result
from pytest_bdd import scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/cli/help.feature")


class HelpContext:
    """Context object for help BDD scenarios."""

    result: Result | None = None
    stdout: str = ""


@when("I run the help command with no arguments", target_fixture="ctx")
def when_run_help_no_args(cli_runner: CliRunner) -> HelpContext:
    """Run the help CLI command with no arguments.

    Returns:
        HelpContext with command result.
    """
    ctx = HelpContext()
    ctx.result = cli_runner.invoke(cli_main.app, ["help"])
    ctx.stdout = ctx.result.stdout
    return ctx


@when('I run the help command for "version"', target_fixture="ctx")
def when_run_help_version(cli_runner: CliRunner) -> HelpContext:
    """Run the help CLI command for version.

    Returns:
        HelpContext with command result.
    """
    ctx = HelpContext()
    ctx.result = cli_runner.invoke(cli_main.app, ["help", "version"])
    ctx.stdout = ctx.result.stdout
    return ctx


@when('I run the help command for "nonexistent"', target_fixture="ctx")
def when_run_help_nonexistent(cli_runner: CliRunner) -> HelpContext:
    """Run the help CLI command for nonexistent command.

    Returns:
        HelpContext with command result.
    """
    ctx = HelpContext()
    ctx.result = cli_runner.invoke(cli_main.app, ["help", "nonexistent"])
    ctx.stdout = ctx.result.stdout
    return ctx


@then("the output contains command names")
def then_output_contains_command_names(ctx: HelpContext) -> None:
    """Assert the output contains command names."""
    assert "version" in ctx.stdout.lower()
    assert "init" in ctx.stdout.lower()
    assert "help" in ctx.stdout.lower()


@then("the output contains detailed help for version")
def then_output_contains_detailed_help(ctx: HelpContext) -> None:
    """Assert the output contains detailed help for version command."""
    assert "version" in ctx.stdout.lower()
    assert "display" in ctx.stdout.lower() or "show" in ctx.stdout.lower()


@then("the output contains an error message")
def then_output_contains_error_message(ctx: HelpContext) -> None:
    """Assert the output contains an error message."""
    assert "error" in ctx.stdout.lower()


@then("the output contains valid command list")
def then_output_contains_valid_command_list(ctx: HelpContext) -> None:
    """Assert the output contains a list of valid commands."""
    # Should list valid commands to help user find correct command
    assert "version" in ctx.stdout.lower() or "init" in ctx.stdout.lower()
