"""BDD integration tests for benchmark CLI command stub (Task 4-6 phase)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from tests.integration.conftest import write_rentl_config
from typer.testing import CliRunner

import rentl_cli.main as cli_main

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../../features/benchmark/cli_command.feature")


class BenchmarkCLIContext:
    """Context object for benchmark CLI BDD scenarios."""

    result: Result | None = None
    stdout: str = ""
    config_dir: Path | None = None


@given("a valid rentl configuration exists", target_fixture="ctx")
def given_valid_config(tmp_workspace: Path) -> BenchmarkCLIContext:
    """Create a valid rentl configuration.

    Returns:
        BenchmarkCLIContext with config directory.
    """
    ctx = BenchmarkCLIContext()
    ctx.config_dir = tmp_workspace.parent
    write_rentl_config(ctx.config_dir, tmp_workspace)

    # Create necessary workspace directories
    (tmp_workspace / "input").mkdir(exist_ok=True)
    (tmp_workspace / "out").mkdir(exist_ok=True)
    (tmp_workspace / "logs").mkdir(exist_ok=True)
    (tmp_workspace / "prompts").mkdir(exist_ok=True)
    (tmp_workspace / "agents").mkdir(exist_ok=True)

    return ctx


@when("I run benchmark command")
def when_run_benchmark_basic(ctx: BenchmarkCLIContext, cli_runner: CliRunner) -> None:
    """Run benchmark CLI command.

    Args:
        ctx: Benchmark CLI context.
        cli_runner: CLI test runner.
    """
    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "benchmark",
        ],
    )
    ctx.stdout = ctx.result.stdout + ctx.result.stderr


@then("the command exits with status 2")
def then_command_exits_with_usage_error(ctx: BenchmarkCLIContext) -> None:
    """Verify command exited with status 2 (usage error).

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.result is not None
    assert ctx.result.exit_code == 2, (
        f"Expected exit code 2, got {ctx.result.exit_code}"
    )


@then("the output indicates a subcommand is required")
def then_output_indicates_subcommand_required(ctx: BenchmarkCLIContext) -> None:
    """Verify output indicates a subcommand is required.

    Args:
        ctx: Benchmark CLI context.
    """
    # Typer shows usage info mentioning COMMAND when no subcommand is provided
    assert "COMMAND" in ctx.stdout
