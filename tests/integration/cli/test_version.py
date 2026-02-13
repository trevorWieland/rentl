"""BDD integration tests for version CLI command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import Result
from pytest_bdd import scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main
from rentl_core import VERSION

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/cli/version.feature")


class VersionContext:
    """Context object for version BDD scenarios."""

    result: Result | None = None
    stdout: str = ""


@when("I run the version command", target_fixture="ctx")
def when_run_version(cli_runner: CliRunner) -> VersionContext:
    """Run the version CLI command.

    Returns:
        VersionContext with command result.
    """
    ctx = VersionContext()
    ctx.result = cli_runner.invoke(cli_main.app, ["version"])
    ctx.stdout = ctx.result.stdout
    return ctx


@then("the output contains the version string")
def then_output_contains_version(ctx: VersionContext) -> None:
    """Assert the output contains the version."""
    assert str(VERSION) in ctx.stdout
