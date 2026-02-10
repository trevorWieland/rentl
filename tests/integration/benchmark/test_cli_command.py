"""BDD integration tests for benchmark CLI command stub (Task 4-6 phase)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

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
    mock_loader: MagicMock | None = None


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


@when("I run benchmark download with kebab-case eval-set name")
def when_run_benchmark_download_kebab_case(
    ctx: BenchmarkCLIContext, cli_runner: CliRunner, monkeypatch: MagicMock
) -> None:
    """Run benchmark download with kebab-case eval-set name.

    Args:
        ctx: Benchmark CLI context.
        cli_runner: CLI test runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    # Mock the EvalSetLoader to verify it receives snake_case
    mock_manifest = MagicMock()
    mock_manifest.scripts = {"script-a1-monday.rpy": "abc123"}
    mock_slices = MagicMock()
    mock_slices.slices = {"demo": MagicMock(scripts=[])}

    with patch("rentl_cli.main.EvalSetLoader") as mock_loader:
        mock_loader.load_manifest = MagicMock(return_value=mock_manifest)
        mock_loader.load_slices = MagicMock(return_value=mock_slices)
        mock_loader.get_slice_scripts = MagicMock(return_value=["script-a1-monday.rpy"])

        # Mock the downloader
        with patch("rentl_cli.main.KatawaShoujoDownloader") as mock_downloader_class:
            mock_downloader = MagicMock()
            mock_downloader.download_scripts = AsyncMock(
                return_value={"script-a1-monday.rpy": Path("/tmp/script-a1-monday.rpy")}
            )
            mock_downloader_class.return_value = mock_downloader

            # Mock the parser
            with patch("rentl_cli.main.RenpyDialogueParser") as mock_parser_class:
                mock_parser = MagicMock()
                mock_parser.parse_script = MagicMock(return_value=[])
                mock_parser_class.return_value = mock_parser

                ctx.result = cli_runner.invoke(
                    cli_main.app,
                    [
                        "benchmark",
                        "download",
                        "--eval-set",
                        "katawa-shoujo",
                        "--slice",
                        "demo",
                    ],
                )
                ctx.stdout = ctx.result.stdout + ctx.result.stderr

                # Store the mock for assertion
                ctx.mock_loader = mock_loader


@then("the command normalizes to snake_case internally")
def then_command_normalizes_to_snake_case(ctx: BenchmarkCLIContext) -> None:
    """Verify the command normalized kebab-case to snake_case.

    Args:
        ctx: Benchmark CLI context.
    """
    # Verify load_manifest was called with snake_case
    ctx.mock_loader.load_manifest.assert_called_once_with("katawa_shoujo")
    ctx.mock_loader.load_slices.assert_called_once_with("katawa_shoujo")


@then("the download succeeds")
def then_download_succeeds(ctx: BenchmarkCLIContext) -> None:
    """Verify the download command succeeded.

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.result is not None
    assert ctx.result.exit_code == 0, (
        f"Expected exit code 0, got {ctx.result.exit_code}\nOutput: {ctx.stdout}"
    )
