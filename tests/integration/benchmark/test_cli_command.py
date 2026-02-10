"""BDD integration tests for benchmark CLI command."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from tests.integration.conftest import write_rentl_config
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_schemas.benchmark.rubric import (
    HeadToHeadResult,
    LineScore,
    RubricDimension,
    RubricScore,
)
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.llm import LlmPromptResponse

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/benchmark/cli_command.feature")


class BenchmarkCLIContext:
    """Context object for benchmark CLI BDD scenarios."""

    result: Result | None = None
    stdout: str = ""
    config_dir: Path | None = None
    output_path: Path | None = None
    mock_runtime: MagicMock | None = None
    mock_downloader: MagicMock | None = None
    mock_parser: MagicMock | None = None
    mock_judge: MagicMock | None = None
    mock_mtl_generator: MagicMock | None = None
    api_key_unset: bool = False


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


@given("a benchmark eval set is available")
def given_eval_set_available(ctx: BenchmarkCLIContext) -> None:
    """Mock the eval set loader to provide manifest and slices.

    Args:
        ctx: Benchmark CLI context.
    """
    # The actual eval set files are committed in rentl-core, so no mocking needed
    # for EvalSetLoader.load_manifest and load_slices
    pass


@given("LLM endpoints are mocked")
def given_llm_mocked(ctx: BenchmarkCLIContext, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock LLM runtime and benchmark components.

    Args:
        ctx: Benchmark CLI context with mocks.
        monkeypatch: Pytest monkeypatch fixture.
    """
    # Mock downloader
    mock_downloader = MagicMock()
    mock_download_scripts = AsyncMock(
        return_value={
            "script-a1-monday.rpy": Path("/fake/script-a1-monday.rpy"),
        }
    )
    mock_downloader.download_scripts = mock_download_scripts

    # Mock parser
    mock_parser = MagicMock()
    mock_source_lines = [
        SourceLine(
            scene_id="scripta1monday_1",
            line_id="scripta1monday_550",
            text="こんにちは",
            speaker=None,
        ),
        SourceLine(
            scene_id="scripta1monday_1",
            line_id="scripta1monday_551",
            text="さようなら",
            speaker="hi",
        ),
    ]
    mock_parser.parse_script.return_value = mock_source_lines

    # Mock MTL generator
    mock_mtl_generator = MagicMock()
    mock_mtl_translations = [
        TranslatedLine(
            scene_id="scripta1monday_1",
            line_id="scripta1monday_550",
            text="Hello",
            speaker=None,
            source_text="こんにちは",
        ),
        TranslatedLine(
            scene_id="scripta1monday_1",
            line_id="scripta1monday_551",
            text="Goodbye",
            speaker="hi",
            source_text="さようなら",
        ),
    ]
    mock_generate_baseline = AsyncMock(return_value=mock_mtl_translations)
    mock_mtl_generator.generate_baseline = mock_generate_baseline

    # Mock judge
    mock_judge = MagicMock()
    mock_line_score = LineScore(
        line_id="scripta1monday_550",
        source_text="こんにちは",
        translation="Hello",
        reference="Hello there",
        scores=[
            RubricScore(
                dimension=RubricDimension.ACCURACY,
                score=5,
                reasoning="Perfect match",
            ),
            RubricScore(
                dimension=RubricDimension.STYLE_FIDELITY,
                score=4,
                reasoning="Good style",
            ),
            RubricScore(
                dimension=RubricDimension.CONSISTENCY,
                score=5,
                reasoning="Consistent terminology",
            ),
        ],
    )
    mock_score_translation = AsyncMock(return_value=mock_line_score)
    mock_judge.score_translation = mock_score_translation

    mock_h2h_result = HeadToHeadResult(
        line_id="scripta1monday_550",
        source_text="こんにちは",
        translation_a="Hello",
        translation_b="Hello there",
        winner="B",
        reasoning="Translation B is more natural",
        dimension_winners={
            RubricDimension.ACCURACY: "tie",
            RubricDimension.STYLE_FIDELITY: "B",
            RubricDimension.CONSISTENCY: "tie",
        },
    )
    mock_compare = AsyncMock(return_value=mock_h2h_result)
    mock_judge.compare_head_to_head = mock_compare

    # Mock LLM runtime
    mock_runtime = MagicMock()
    mock_response = LlmPromptResponse(
        model_id="gpt-4o-mini",
        output_text="Mock translation",
    )
    mock_prompt_async = AsyncMock(return_value=mock_response)
    mock_runtime.prompt_async = mock_prompt_async

    ctx.mock_downloader = mock_downloader
    ctx.mock_parser = mock_parser
    ctx.mock_mtl_generator = mock_mtl_generator
    ctx.mock_judge = mock_judge
    ctx.mock_runtime = mock_runtime

    # Patch the classes in the CLI module
    monkeypatch.setattr(
        "rentl_cli.main.KatawaShoujoDownloader", lambda: mock_downloader
    )
    monkeypatch.setattr("rentl_cli.main.RenpyDialogueParser", lambda: mock_parser)
    monkeypatch.setattr("rentl_cli.main.OpenAICompatibleRuntime", lambda: mock_runtime)

    # Patch MTLBaselineGenerator and RubricJudge constructors
    def mock_mtl_constructor(*args: object, **kwargs: object) -> MagicMock:
        return mock_mtl_generator

    def mock_judge_constructor(*args: object, **kwargs: object) -> MagicMock:
        return mock_judge

    monkeypatch.setattr("rentl_cli.main.MTLBaselineGenerator", mock_mtl_constructor)
    monkeypatch.setattr("rentl_cli.main.RubricJudge", mock_judge_constructor)


@given("output path is specified")
def given_output_path(ctx: BenchmarkCLIContext, tmp_path: Path) -> None:
    """Specify output path for JSON report.

    Args:
        ctx: Benchmark CLI context.
        tmp_path: Temporary directory for output.
    """
    ctx.output_path = tmp_path / "benchmark_report.json"


@given("OPENAI_API_KEY is not set")
def given_no_api_key(ctx: BenchmarkCLIContext, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset OPENAI_API_KEY environment variable.

    Args:
        ctx: Benchmark CLI context.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ctx.api_key_unset = True


@when("I run benchmark command with demo slice")
def when_run_benchmark_demo(ctx: BenchmarkCLIContext, cli_runner: CliRunner) -> None:
    """Run benchmark CLI command with demo slice.

    Args:
        ctx: Benchmark CLI context.
        cli_runner: CLI test runner.
    """
    assert ctx.config_dir is not None
    config_path = ctx.config_dir / "rentl.toml"

    # Set API key for test
    os.environ["OPENAI_API_KEY"] = "test-key"

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


@when("I run benchmark command with JSON output")
def when_run_benchmark_json_output(
    ctx: BenchmarkCLIContext, cli_runner: CliRunner
) -> None:
    """Run benchmark CLI command with JSON output path.

    Args:
        ctx: Benchmark CLI context.
        cli_runner: CLI test runner.
    """
    assert ctx.config_dir is not None
    assert ctx.output_path is not None
    config_path = ctx.config_dir / "rentl.toml"

    # Set API key for test
    os.environ["OPENAI_API_KEY"] = "test-key"

    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "benchmark",
            "--eval-set",
            "katawa-shoujo",
            "--slice",
            "demo",
            "--output",
            str(ctx.output_path),
            "--config",
            str(config_path),
        ],
    )
    ctx.stdout = ctx.result.stdout


@when("I run benchmark command")
def when_run_benchmark_basic(ctx: BenchmarkCLIContext, cli_runner: CliRunner) -> None:
    """Run benchmark CLI command without special options.

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


@when("I run benchmark command with invalid slice")
def when_run_benchmark_invalid_slice(
    ctx: BenchmarkCLIContext, cli_runner: CliRunner
) -> None:
    """Run benchmark CLI command with invalid slice name.

    Args:
        ctx: Benchmark CLI context.
        cli_runner: CLI test runner.
    """
    assert ctx.config_dir is not None
    config_path = ctx.config_dir / "rentl.toml"

    # Set API key for test
    os.environ["OPENAI_API_KEY"] = "test-key"

    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "benchmark",
            "--eval-set",
            "katawa-shoujo",
            "--slice",
            "invalid-slice-name",
            "--config",
            str(config_path),
        ],
    )
    ctx.stdout = ctx.result.stdout


@then("the command succeeds")
def then_command_succeeds(ctx: BenchmarkCLIContext) -> None:
    """Verify command exited successfully.

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.result is not None
    assert ctx.result.exit_code == 0, f"Command failed: {ctx.stdout}"


@then("the command fails")
def then_command_fails(ctx: BenchmarkCLIContext) -> None:
    """Verify command exited with error.

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.result is not None
    assert ctx.result.exit_code != 0


@then("the output includes download progress")
def then_output_includes_download(ctx: BenchmarkCLIContext) -> None:
    """Verify output includes download step.

    Args:
        ctx: Benchmark CLI context.
    """
    assert "Step 1/5" in ctx.stdout
    assert "Downloading eval set" in ctx.stdout


@then("the output includes MTL baseline generation")
def then_output_includes_mtl(ctx: BenchmarkCLIContext) -> None:
    """Verify output includes MTL generation step.

    Args:
        ctx: Benchmark CLI context.
    """
    assert "Step 2/5" in ctx.stdout
    assert "Generating MTL baseline" in ctx.stdout


@then("the output includes judging progress")
def then_output_includes_judging(ctx: BenchmarkCLIContext) -> None:
    """Verify output includes judging step.

    Args:
        ctx: Benchmark CLI context.
    """
    assert "Step 4/5" in ctx.stdout
    assert "Judging translations" in ctx.stdout


@then("the output includes benchmark report summary")
def then_output_includes_report(ctx: BenchmarkCLIContext) -> None:
    """Verify output includes final report.

    Args:
        ctx: Benchmark CLI context.
    """
    assert "Step 5/5" in ctx.stdout
    assert "Benchmark Report" in ctx.stdout or "report" in ctx.stdout.lower()


@then("dimension aggregates are displayed")
def then_dimension_aggregates_displayed(ctx: BenchmarkCLIContext) -> None:
    """Verify dimension aggregates are shown.

    Args:
        ctx: Benchmark CLI context.
    """
    # Output should mention rubric dimensions
    assert (
        "accuracy" in ctx.stdout.lower()
        or "style" in ctx.stdout.lower()
        or "consistency" in ctx.stdout.lower()
    )


@then("a JSON report file is created")
def then_json_report_created(ctx: BenchmarkCLIContext) -> None:
    """Verify JSON report file exists.

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.output_path is not None
    assert ctx.output_path.exists(), f"Report file not found at {ctx.output_path}"


@then("the report contains per-line scores")
def then_report_has_line_scores(ctx: BenchmarkCLIContext) -> None:
    """Verify report contains per-line scores.

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.output_path is not None
    with open(ctx.output_path) as f:
        report = json.load(f)

    assert "mtl_results" in report or "rentl_results" in report
    # Check that at least one system has line-level scores
    if report.get("mtl_results"):
        first_result = report["mtl_results"][0]
        assert "scores" in first_result
        assert len(first_result["scores"]) > 0


@then("the report contains dimension aggregates")
def then_report_has_aggregates(ctx: BenchmarkCLIContext) -> None:
    """Verify report contains dimension aggregates.

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.output_path is not None
    with open(ctx.output_path) as f:
        report = json.load(f)

    # Check for aggregated metrics structure
    assert (
        "mtl_aggregates" in report
        or "rentl_aggregates" in report
        or "dimension_aggregates" in report
    )


@then("the report contains head-to-head comparison")
def then_report_has_h2h(ctx: BenchmarkCLIContext) -> None:
    """Verify report contains head-to-head comparison.

    Args:
        ctx: Benchmark CLI context.
    """
    assert ctx.output_path is not None
    with open(ctx.output_path) as f:
        report = json.load(f)

    # Check for head-to-head structure
    assert (
        "head_to_head_results" in report
        or "head_to_head_summary" in report
        or "comparison" in report
    )


@then("error message indicates missing API key")
def then_error_missing_api_key(ctx: BenchmarkCLIContext) -> None:
    """Verify error message mentions missing API key.

    Args:
        ctx: Benchmark CLI context.
    """
    assert "OPENAI_API_KEY" in ctx.stdout or "API key" in ctx.stdout


@then("error message lists available slices")
def then_error_lists_slices(ctx: BenchmarkCLIContext) -> None:
    """Verify error message lists available slices.

    Args:
        ctx: Benchmark CLI context.
    """
    assert "not found" in ctx.stdout
    assert "Available" in ctx.stdout or "available" in ctx.stdout
