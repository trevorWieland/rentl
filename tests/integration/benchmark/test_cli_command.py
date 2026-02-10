"""BDD integration tests for benchmark CLI command stub (Task 4-6 phase)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from tests.integration.conftest import write_rentl_config
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_schemas.benchmark import HeadToHeadResult

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../../features/benchmark/cli_command.feature")


class BenchmarkCLIContext:
    """Context object for benchmark CLI BDD scenarios."""

    def __init__(self) -> None:
        """Initialize context."""
        self.result: Result | None = None
        self.stdout: str = ""
        self.config_dir: Path | None = None
        self.mock_loader: MagicMock | None = None
        self.progress_updates: list[int] = []
        self.output_file_a: Path | None = None
        self.output_file_b: Path | None = None


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
    assert ctx.mock_loader is not None
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


@given("two translation output files exist")
def given_two_translation_output_files(
    ctx: BenchmarkCLIContext, tmp_path: Path
) -> None:
    """Create two mock translation output files.

    Args:
        ctx: Benchmark CLI context.
        tmp_path: Temporary directory for test files.
    """
    # Create minimal translation output files with 3 lines each
    lines_a = [
        {
            "line_id": "scene_1",
            "scene_id": "scene",
            "source_text": "Hello",
            "text": "Translation A line 1",
        },
        {
            "line_id": "scene_2",
            "scene_id": "scene",
            "source_text": "World",
            "text": "Translation A line 2",
        },
        {
            "line_id": "scene_3",
            "scene_id": "scene",
            "source_text": "Test",
            "text": "Translation A line 3",
        },
    ]

    lines_b = [
        {
            "line_id": "scene_1",
            "scene_id": "scene",
            "source_text": "Hello",
            "text": "Translation B line 1",
        },
        {
            "line_id": "scene_2",
            "scene_id": "scene",
            "source_text": "World",
            "text": "Translation B line 2",
        },
        {
            "line_id": "scene_3",
            "scene_id": "scene",
            "source_text": "Test",
            "text": "Translation B line 3",
        },
    ]

    ctx.output_file_a = tmp_path / "output_a.jsonl"
    ctx.output_file_b = tmp_path / "output_b.jsonl"

    with ctx.output_file_a.open("w") as f:
        for line in lines_a:
            f.write(json.dumps(line) + "\n")

    with ctx.output_file_b.open("w") as f:
        for line in lines_b:
            f.write(json.dumps(line) + "\n")


@when("I run benchmark compare with staggered judge responses")
def when_run_benchmark_compare_staggered(
    ctx: BenchmarkCLIContext, cli_runner: CliRunner, monkeypatch: MagicMock
) -> None:
    """Run benchmark compare with mocked judge that completes out-of-order.

    Args:
        ctx: Benchmark CLI context.
        cli_runner: CLI test runner.
        monkeypatch: Pytest monkeypatch fixture.
    """
    # Track progress updates
    original_update = None

    def track_progress_update(task: object, **kwargs: int | str) -> None:
        """Track progress update calls."""
        if "completed" in kwargs:
            ctx.progress_updates.append(int(kwargs["completed"]))
        if original_update:
            original_update(task, **kwargs)

    # Mock judge to simulate staggered completions
    async def mock_compare_head_to_head(**kwargs: str) -> HeadToHeadResult:
        """Mock judge comparison with staggered delays.

        Returns:
            HeadToHeadResult with test data.
        """
        line_id = kwargs.get("line_id", "")
        source_text = kwargs.get("source_text", "")
        translation_1 = kwargs.get("translation_1", "")
        translation_2 = kwargs.get("translation_2", "")
        candidate_1_name = kwargs.get("candidate_1_name", "candidate-a")
        candidate_2_name = kwargs.get("candidate_2_name", "candidate-b")

        # Different delays to create out-of-order completion
        if line_id == "scene_1":
            await asyncio.sleep(0.03)  # Slowest
        elif line_id == "scene_2":
            await asyncio.sleep(0.02)  # Medium
        else:
            await asyncio.sleep(0.01)  # Fastest

        return HeadToHeadResult(
            line_id=line_id,
            source_text=source_text,
            candidate_a_name=candidate_1_name,
            candidate_b_name=candidate_2_name,
            translation_a=translation_1,
            translation_b=translation_2,
            winner="A",
            reasoning="Test reasoning",
            dimension_winners={},
        )

    # Patch RubricJudge
    mock_judge = MagicMock()
    mock_judge.compare_head_to_head.side_effect = mock_compare_head_to_head

    with (
        patch("rentl_cli.main.RubricJudge", return_value=mock_judge),
        patch(
            "rentl_cli.main.Progress.update", side_effect=track_progress_update
        ) as mock_update,
    ):
        original_update = mock_update

        ctx.result = cli_runner.invoke(
            cli_main.app,
            [
                "benchmark",
                "compare",
                str(ctx.output_file_a),
                str(ctx.output_file_b),
                "--candidate-names",
                "candidate-a,candidate-b",
            ],
            env={"OPENAI_API_KEY": "test-key"},
        )
        ctx.stdout = ctx.result.stdout + ctx.result.stderr


@then("progress updates are monotonically increasing")
def then_progress_updates_monotonic(ctx: BenchmarkCLIContext) -> None:
    """Verify progress updates never decrease.

    Args:
        ctx: Benchmark CLI context.
    """
    assert len(ctx.progress_updates) > 0, "No progress updates recorded"

    for i in range(1, len(ctx.progress_updates)):
        prev = ctx.progress_updates[i - 1]
        curr = ctx.progress_updates[i]
        assert curr >= prev, (
            f"Progress update regressed from {prev} to {curr} at index {i}"
        )


@then("final progress reaches 100%")
def then_final_progress_100(ctx: BenchmarkCLIContext) -> None:
    """Verify final progress reaches the total.

    Args:
        ctx: Benchmark CLI context.
    """
    # With 3 lines and 2 candidates, we have 3 comparisons
    expected_total = 3
    assert len(ctx.progress_updates) > 0, "No progress updates recorded"
    assert ctx.progress_updates[-1] == expected_total, (
        f"Final progress was {ctx.progress_updates[-1]}, expected {expected_total}"
    )
