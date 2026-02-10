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
    assert ctx.config_dir is not None
    config_path = ctx.config_dir / "rentl.toml"

    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "benchmark",
            "--eval-set",
            "katawa-shoujo",
            "--slice",
            "demo",
            "--config",
            str(config_path),
        ],
    )
    ctx.stdout = ctx.result.stdout


@then("the command exits with status 1")
def then_command_exits_with_error(ctx: BenchmarkCLIContext) -> None:
    """Verify command exited with status 1.

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.result is not None
    assert ctx.result.exit_code == 1, (
        f"Expected exit code 1, got {ctx.result.exit_code}"
    )


@then("the output indicates command is being rewritten")
def then_output_indicates_rewrite(ctx: BenchmarkCLIContext) -> None:
    """Verify output indicates the command is being rewritten.

    Args:
        ctx: Benchmark CLI context.
    """
    assert "being rewritten" in ctx.stdout
    assert "Task 7" in ctx.stdout
