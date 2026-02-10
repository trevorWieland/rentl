"""BDD quality tests for benchmark harness with real LLM calls.

These tests verify that the benchmark comparison mechanics work correctly
with real LLMs:
- Judge head-to-head comparison returns per-line results with reasoning
- All rubric dimensions have winners
- Report structure includes pairwise summaries and Elo ratings

IMPORTANT: These tests require a real LLM endpoint to be running.
Set RENTL_QUALITY_API_KEY and RENTL_QUALITY_BASE_URL environment variables
before running. The test will be skipped if these are not configured.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_schemas.benchmark.report import BenchmarkReport
from rentl_schemas.io import TranslatedLine

if TYPE_CHECKING:
    from click.testing import Result


# Link feature file
scenarios("../features/benchmark/benchmark_quality.feature")

# Skip entire module if quality test environment is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("RENTL_QUALITY_API_KEY") or not os.getenv("RENTL_QUALITY_BASE_URL"),
    reason="Requires RENTL_QUALITY_API_KEY and RENTL_QUALITY_BASE_URL to be set",
)


class BenchmarkContext:
    """Test context for benchmark quality tests."""

    def __init__(self, tmp_path: Path) -> None:
        """Initialize test context."""
        self.tmp_path = tmp_path
        self.output_a_path: Path | None = None
        self.output_b_path: Path | None = None
        self.report_path: Path | None = None
        self.result: Result | None = None
        self.report: BenchmarkReport | None = None


@pytest.fixture
def ctx(tmp_path: Path) -> BenchmarkContext:
    """Create test context.

    Returns:
        BenchmarkContext: Test context for benchmark quality tests.
    """
    return BenchmarkContext(tmp_path)


@given("sample translation output files exist")
def create_sample_outputs(ctx: BenchmarkContext) -> None:
    """Create sample translation output JSONL files for comparison."""
    # Create two sample translation outputs with small differences
    # These represent outputs from different translation systems on the same source

    sample_lines_a = [
        TranslatedLine(
            line_id="scene_1_1",
            scene_id="scene_1",
            source_text="こんにちは、世界。",
            text="Hello, world.",
        ),
        TranslatedLine(
            line_id="scene_1_2",
            scene_id="scene_1",
            source_text="今日はいい天気ですね。",
            text="It's nice weather today.",
        ),
        TranslatedLine(
            line_id="scene_1_3",
            scene_id="scene_1",
            source_text="ありがとうございます。",
            text="Thank you very much.",
        ),
    ]

    sample_lines_b = [
        TranslatedLine(
            line_id="scene_1_1",
            scene_id="scene_1",
            source_text="こんにちは、世界。",
            text="Hello, World.",  # Different capitalization
        ),
        TranslatedLine(
            line_id="scene_1_2",
            scene_id="scene_1",
            source_text="今日はいい天気ですね。",
            text="The weather is nice today.",  # Different structure
        ),
        TranslatedLine(
            line_id="scene_1_3",
            scene_id="scene_1",
            source_text="ありがとうございます。",
            text="Thanks.",  # More casual
        ),
    ]

    # Write output A
    ctx.output_a_path = ctx.tmp_path / "output_a.jsonl"
    with ctx.output_a_path.open("w") as f:
        for line in sample_lines_a:
            f.write(line.model_dump_json() + "\n")

    # Write output B
    ctx.output_b_path = ctx.tmp_path / "output_b.jsonl"
    with ctx.output_b_path.open("w") as f:
        for line in sample_lines_b:
            f.write(line.model_dump_json() + "\n")


@given("real LLM endpoints are configured")
def verify_llm_endpoints(ctx: BenchmarkContext) -> None:
    """Verify that real LLM endpoint configuration is available."""
    assert os.getenv("RENTL_QUALITY_API_KEY"), "RENTL_QUALITY_API_KEY must be set"
    assert os.getenv("RENTL_QUALITY_BASE_URL"), "RENTL_QUALITY_BASE_URL must be set"


@when("I run benchmark compare on the output files")
def run_benchmark_compare(ctx: BenchmarkContext) -> None:
    """Run benchmark compare command with real LLM judge."""
    ctx.report_path = ctx.tmp_path / "benchmark_report.json"

    runner = CliRunner()
    # Use config-based mode to test proper endpoint resolution
    config_path = Path("rentl.toml")
    result = runner.invoke(
        cli_main.app,
        [
            "benchmark",
            "compare",
            str(ctx.output_a_path),
            str(ctx.output_b_path),
            "--config",
            str(config_path),
            "--judge-model",
            "gpt-4o-mini",
            "--output",
            str(ctx.report_path),
            "--candidate-names",
            "candidate-a,candidate-b",
        ],
        catch_exceptions=False,
    )
    ctx.result = result

    # Parse the JSON report if it was created
    if ctx.report_path and ctx.report_path.exists():
        report_data = json.loads(ctx.report_path.read_text())
        ctx.report = BenchmarkReport.model_validate(report_data)


@then("the benchmark completes successfully")
def check_benchmark_success(ctx: BenchmarkContext) -> None:
    """Verify that the benchmark command completed successfully."""
    assert ctx.result is not None
    assert ctx.result.exit_code == 0, f"Command failed: {ctx.result.output}"


@then("per-line head-to-head results are present")
def check_per_line_results(ctx: BenchmarkContext) -> None:
    """Verify that all evaluated lines have head-to-head results."""
    assert ctx.report is not None, "No report was generated"
    assert len(ctx.report.head_to_head_results) > 0, "No head-to-head results found"
    # Should have 3 lines compared (from sample outputs)
    assert len(ctx.report.head_to_head_results) == 3, (
        f"Expected 3 head-to-head results, got {len(ctx.report.head_to_head_results)}"
    )


@then("each result includes judge reasoning")
def check_judge_reasoning(ctx: BenchmarkContext) -> None:
    """Verify that each head-to-head result includes judge reasoning."""
    assert ctx.report is not None
    for result in ctx.report.head_to_head_results:
        assert result.reasoning, f"Missing reasoning for line {result.line_id}"
        # Reasoning should be non-empty and substantive
        assert len(result.reasoning) > 10, (
            f"Reasoning for line {result.line_id} is too short: {result.reasoning}"
        )


@then("all rubric dimensions have winners")
def check_rubric_dimensions(ctx: BenchmarkContext) -> None:
    """Verify that all rubric dimensions have winner selections."""
    assert ctx.report is not None
    for result in ctx.report.head_to_head_results:
        # Should have 3 dimensions: accuracy, style_fidelity, consistency
        assert len(result.dimension_winners) == 3, (
            f"Line {result.line_id} should have 3 dimension winners, "
            f"got {len(result.dimension_winners)}"
        )
        # Each dimension winner should be valid (A|B|tie per HeadToHeadResult contract)
        for dim, winner in result.dimension_winners.items():
            assert winner in ["A", "B", "tie"], (
                f"Invalid winner '{winner}' for dimension {dim} "
                f"on line {result.line_id}. Expected 'A', 'B', or 'tie' "
                f"(randomized presentation positions, not candidate names)"
            )


@then("pairwise summaries include win rates")
def check_pairwise_summaries(ctx: BenchmarkContext) -> None:
    """Verify that pairwise summaries include win rates."""
    assert ctx.report is not None
    # Should have 1 pairwise summary (A vs B)
    assert len(ctx.report.pairwise_summaries) == 1, (
        f"Expected 1 pairwise summary, got {len(ctx.report.pairwise_summaries)}"
    )

    summary = ctx.report.pairwise_summaries[0]
    # Check that winners are tallied
    total_wins = summary.candidate_a_wins + summary.candidate_b_wins + summary.ties
    assert total_wins == summary.total_comparisons, (
        "Winner counts don't sum to total comparisons"
    )

    # Check dimension win rates are present (3 dimensions)
    assert len(summary.dimension_win_rates) == 3, (
        "Should have win rates for all 3 dimensions"
    )


@then("Elo ratings are computed")
def check_elo_ratings(ctx: BenchmarkContext) -> None:
    """Verify that Elo ratings are computed for all candidates."""
    assert ctx.report is not None
    # Should have 2 Elo ratings (one per candidate)
    assert len(ctx.report.elo_ratings) == 2, (
        f"Expected 2 Elo ratings, got {len(ctx.report.elo_ratings)}"
    )

    # Check that overall ranking is derived from Elo
    assert len(ctx.report.overall_ranking) == 2, (
        f"Expected 2 candidates in ranking, got {len(ctx.report.overall_ranking)}"
    )
    assert ctx.report.overall_ranking[0] in ["candidate-a", "candidate-b"], (
        f"Invalid top-ranked candidate: {ctx.report.overall_ranking[0]}"
    )
    assert ctx.report.overall_ranking[1] in ["candidate-a", "candidate-b"], (
        f"Invalid second-ranked candidate: {ctx.report.overall_ranking[1]}"
    )
