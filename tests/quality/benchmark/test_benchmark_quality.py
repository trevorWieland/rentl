"""BDD quality tests for benchmark harness with real LLM calls.

These tests verify that the benchmark mechanics work correctly with real LLMs:
- Judge scoring returns proper per-line scores with reasoning
- All rubric dimensions are evaluated
- Report structure is complete

IMPORTANT: These tests require a real LLM endpoint to be running.
Set RENTL_QUALITY_API_KEY and RENTL_QUALITY_BASE_URL environment variables
before running. The test will be skipped if these are not configured.
"""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_schemas.benchmark.report import BenchmarkReport
from rentl_schemas.benchmark.rubric import RubricDimension

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
        self.config_path: Path | None = None
        self.output_path: Path | None = None
        self.result: Result | None = None
        self.report: BenchmarkReport | None = None


@pytest.fixture
def ctx(tmp_path: Path) -> BenchmarkContext:
    """Create test context.

    Returns:
        BenchmarkContext: Test context for benchmark quality tests.
    """
    return BenchmarkContext(tmp_path)


@given("a valid rentl configuration exists")
def create_rentl_config(ctx: BenchmarkContext) -> None:
    """Create a minimal rentl configuration for benchmark testing."""
    base_url = os.getenv("RENTL_QUALITY_BASE_URL", "http://localhost:8001/v1")
    workspace_dir = ctx.tmp_path / "workspace"
    workspace_dir.mkdir()

    config_path = ctx.tmp_path / "rentl.toml"
    content = textwrap.dedent(
        f"""\
        [project]
        schema_version = {{ major = 0, minor = 1, patch = 0 }}
        project_name = "benchmark-quality-test"

        [project.paths]
        workspace_dir = "{workspace_dir}"
        input_path = "input.jsonl"
        output_dir = "out"
        logs_dir = "logs"

        [project.formats]
        input_format = "jsonl"
        output_format = "jsonl"

        [project.languages]
        source_language = "ja"
        target_languages = ["en"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "{base_url}"
        api_key_env = "RENTL_QUALITY_API_KEY"

        [pipeline.default_model]
        model_id = "gpt-4o-mini"
        endpoint_ref = "primary"
        """
    )
    config_path.write_text(content)
    ctx.config_path = config_path


@given("the demo slice is configured")
def verify_demo_slice_configured(ctx: BenchmarkContext) -> None:
    """Verify that the demo slice is configured in the eval set."""
    # The demo slice is committed in the repo at:
    # packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json
    # This step just documents that we're relying on it existing
    pass


@given("real LLM endpoints are configured")
def verify_llm_endpoints(ctx: BenchmarkContext) -> None:
    """Verify that real LLM endpoint configuration is available."""
    assert os.getenv("RENTL_QUALITY_API_KEY"), "RENTL_QUALITY_API_KEY must be set"
    assert os.getenv("RENTL_QUALITY_BASE_URL"), "RENTL_QUALITY_BASE_URL must be set"


@when("I run benchmark on the demo slice")
def run_benchmark_demo_slice(ctx: BenchmarkContext) -> None:
    """Run the benchmark command on the demo slice with JSON output."""
    ctx.output_path = ctx.tmp_path / "benchmark_report.json"

    runner = CliRunner()
    result = runner.invoke(
        cli_main.app,
        [
            "--config",
            str(ctx.config_path),
            "benchmark",
            "--eval-set",
            "katawa_shoujo",
            "--slice",
            "demo",
            "--judge-model",
            "gpt-4o-mini",
            "--output",
            str(ctx.output_path),
        ],
        env={
            "RENTL_QUALITY_API_KEY": os.getenv("RENTL_QUALITY_API_KEY", ""),
            "RENTL_QUALITY_BASE_URL": os.getenv("RENTL_QUALITY_BASE_URL", ""),
        },
        catch_exceptions=False,
    )
    ctx.result = result

    # Parse the JSON report if it was created
    if ctx.output_path and ctx.output_path.exists():
        report_data = json.loads(ctx.output_path.read_text())
        ctx.report = BenchmarkReport.model_validate(report_data)


@then("the benchmark completes successfully")
def check_benchmark_success(ctx: BenchmarkContext) -> None:
    """Verify that the benchmark command completed successfully."""
    assert ctx.result is not None
    assert ctx.result.exit_code == 0, f"Command failed: {ctx.result.output}"


@then("per-line scores are present for all evaluated lines")
def check_per_line_scores(ctx: BenchmarkContext) -> None:
    """Verify that all evaluated lines have scores."""
    assert ctx.report is not None, "No report was generated"
    assert ctx.report.mtl_result is not None, "MTL result missing"
    assert ctx.report.rentl_result is not None, "rentl result missing"

    # Check MTL result has scores for all lines
    assert len(ctx.report.mtl_result.line_scores) > 0, "No MTL line scores found"

    # Check rentl result has scores for all lines
    assert len(ctx.report.rentl_result.line_scores) > 0, "No rentl line scores found"

    # Both should have the same number of lines evaluated
    assert len(ctx.report.mtl_result.line_scores) == len(
        ctx.report.rentl_result.line_scores
    ), "MTL and rentl have different number of evaluated lines"


@then("each score includes judge reasoning")
def check_judge_reasoning(ctx: BenchmarkContext) -> None:
    """Verify that each line score includes judge reasoning for all dimensions."""
    assert ctx.report is not None

    # Check MTL result
    for line_score in ctx.report.mtl_result.line_scores:
        for rubric_score in line_score.scores:
            assert rubric_score.reasoning, (
                f"Missing {rubric_score.dimension} reasoning "
                f"for line {line_score.line_id}"
            )

    # Check rentl result
    for line_score in ctx.report.rentl_result.line_scores:
        for rubric_score in line_score.scores:
            assert rubric_score.reasoning, (
                f"Missing {rubric_score.dimension} reasoning "
                f"for line {line_score.line_id}"
            )


@then("all rubric dimensions have scores")
def check_rubric_dimensions(ctx: BenchmarkContext) -> None:
    """Verify that all rubric dimensions are scored."""
    assert ctx.report is not None

    # Check MTL result has all three dimensions
    for line_score in ctx.report.mtl_result.line_scores:
        assert len(line_score.scores) == 3, (
            f"Line {line_score.line_id} should have 3 dimension scores"
        )
        for rubric_score in line_score.scores:
            assert 1 <= rubric_score.score <= 5, (
                f"Invalid {rubric_score.dimension} score for line {line_score.line_id}"
            )

    # Check rentl result has all three dimensions
    for line_score in ctx.report.rentl_result.line_scores:
        assert len(line_score.scores) == 3, (
            f"Line {line_score.line_id} should have 3 dimension scores"
        )
        for rubric_score in line_score.scores:
            assert 1 <= rubric_score.score <= 5, (
                f"Invalid {rubric_score.dimension} score for line {line_score.line_id}"
            )


@then("dimension aggregates are computed")
def check_dimension_aggregates(ctx: BenchmarkContext) -> None:
    """Verify that dimension aggregates are present in the report."""
    assert ctx.report is not None
    assert ctx.report.mtl_result is not None
    assert ctx.report.rentl_result is not None

    # Check MTL aggregates
    assert len(ctx.report.mtl_result.dimension_aggregates) == 3, (
        "MTL should have 3 dimension aggregates"
    )

    # Check rentl aggregates
    assert len(ctx.report.rentl_result.dimension_aggregates) == 3, (
        "rentl should have 3 dimension aggregates"
    )

    # Verify MTL aggregates have mean values > 0
    for agg in ctx.report.mtl_result.dimension_aggregates:
        assert agg.mean > 0, f"MTL {agg.dimension} mean should be > 0"

    # Verify rentl aggregates have mean values > 0
    for agg in ctx.report.rentl_result.dimension_aggregates:
        assert agg.mean > 0, f"rentl {agg.dimension} mean should be > 0"


@then("head-to-head results include winner selections")
def check_head_to_head_results(ctx: BenchmarkContext) -> None:
    """Verify that head-to-head comparison results include winner selections."""
    assert ctx.report is not None
    assert ctx.report.head_to_head_summary is not None

    # Check that we have head-to-head results
    assert ctx.report.head_to_head_summary.total_comparisons > 0, (
        "No head-to-head comparisons found"
    )

    # Check that winners are tallied
    total_wins = (
        ctx.report.head_to_head_summary.system_a_wins
        + ctx.report.head_to_head_summary.system_b_wins
        + ctx.report.head_to_head_summary.ties
    )
    assert total_wins == ctx.report.head_to_head_summary.total_comparisons, (
        "Winner counts don't sum to total comparisons"
    )

    # Check dimension win rates are present
    assert len(ctx.report.head_to_head_summary.dimension_win_rates) == 3, (
        "Should have win rates for all 3 dimensions"
    )

    # Verify all three dimensions have win rate entries
    assert (
        RubricDimension.ACCURACY in ctx.report.head_to_head_summary.dimension_win_rates
    )
    assert (
        RubricDimension.STYLE_FIDELITY
        in ctx.report.head_to_head_summary.dimension_win_rates
    )
    assert (
        RubricDimension.CONSISTENCY
        in ctx.report.head_to_head_summary.dimension_win_rates
    )
