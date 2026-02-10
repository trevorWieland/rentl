"""Unit tests for benchmark report schemas."""

from rentl_schemas.benchmark.report import (
    BenchmarkReport,
    DimensionAggregate,
    HeadToHeadSummary,
    TranslationResult,
)
from rentl_schemas.benchmark.rubric import (
    HeadToHeadResult,
    LineScore,
    RubricDimension,
    RubricScore,
)


def test_dimension_aggregate_valid() -> None:
    """Test DimensionAggregate with valid data."""
    aggregate = DimensionAggregate(
        dimension=RubricDimension.ACCURACY,
        mean=4.2,
        median=4.0,
        stddev=0.8,
        min_score=3,
        max_score=5,
    )
    assert aggregate.dimension == RubricDimension.ACCURACY
    assert aggregate.mean == 4.2
    assert aggregate.median == 4.0
    assert aggregate.min_score == 3
    assert aggregate.max_score == 5


def test_dimension_aggregate_roundtrip() -> None:
    """Test DimensionAggregate serialization roundtrip."""
    original = DimensionAggregate(
        dimension=RubricDimension.STYLE_FIDELITY,
        mean=3.5,
        median=3.5,
        stddev=1.2,
        min_score=1,
        max_score=5,
    )
    json_data = original.model_dump()
    reconstructed = DimensionAggregate.model_validate(json_data)
    assert reconstructed == original


def test_translation_result_valid() -> None:
    """Test TranslationResult with valid data."""
    line_scores = [
        LineScore(
            line_id="line1",
            source_text="源1",
            translation="Trans1",
            scores=[
                RubricScore(
                    dimension=RubricDimension.ACCURACY,
                    score=4,
                    reasoning="Good",
                )
            ],
        ),
        LineScore(
            line_id="line2",
            source_text="源2",
            translation="Trans2",
            scores=[
                RubricScore(
                    dimension=RubricDimension.ACCURACY,
                    score=5,
                    reasoning="Excellent",
                )
            ],
        ),
    ]
    aggregates = [
        DimensionAggregate(
            dimension=RubricDimension.ACCURACY,
            mean=4.5,
            median=4.5,
            stddev=0.5,
            min_score=4,
            max_score=5,
        )
    ]
    result = TranslationResult(
        system_name="rentl",
        line_scores=line_scores,
        dimension_aggregates=aggregates,
    )
    assert result.system_name == "rentl"
    assert len(result.line_scores) == 2
    assert len(result.dimension_aggregates) == 1


def test_translation_result_roundtrip() -> None:
    """Test TranslationResult serialization roundtrip."""
    original = TranslationResult(
        system_name="mtl",
        line_scores=[
            LineScore(
                line_id="test",
                source_text="テスト",
                translation="Test",
                scores=[
                    RubricScore(
                        dimension=RubricDimension.CONSISTENCY,
                        score=3,
                        reasoning="OK",
                    )
                ],
            )
        ],
        dimension_aggregates=[
            DimensionAggregate(
                dimension=RubricDimension.CONSISTENCY,
                mean=3.0,
                median=3.0,
                stddev=0.0,
                min_score=3,
                max_score=3,
            )
        ],
    )
    json_data = original.model_dump()
    reconstructed = TranslationResult.model_validate(json_data)
    assert reconstructed == original


def test_head_to_head_summary_valid() -> None:
    """Test HeadToHeadSummary with valid data."""
    summary = HeadToHeadSummary(
        total_comparisons=100,
        system_a_wins=45,
        system_b_wins=40,
        ties=15,
        dimension_win_rates={
            RubricDimension.ACCURACY: {"A": 0.50, "B": 0.35, "tie": 0.15},
            RubricDimension.STYLE_FIDELITY: {"A": 0.40, "B": 0.45, "tie": 0.15},
        },
    )
    assert summary.total_comparisons == 100
    assert summary.system_a_wins == 45
    assert summary.system_b_wins == 40
    assert summary.ties == 15
    assert len(summary.dimension_win_rates) == 2


def test_head_to_head_summary_no_dimension_rates() -> None:
    """Test HeadToHeadSummary with default empty dimension_win_rates."""
    summary = HeadToHeadSummary(
        total_comparisons=50,
        system_a_wins=25,
        system_b_wins=20,
        ties=5,
    )
    assert summary.dimension_win_rates == {}


def test_head_to_head_summary_roundtrip() -> None:
    """Test HeadToHeadSummary serialization roundtrip."""
    original = HeadToHeadSummary(
        total_comparisons=10,
        system_a_wins=5,
        system_b_wins=4,
        ties=1,
        dimension_win_rates={
            RubricDimension.CONSISTENCY: {"A": 0.6, "B": 0.3, "tie": 0.1},
        },
    )
    json_data = original.model_dump()
    reconstructed = HeadToHeadSummary.model_validate(json_data)
    assert reconstructed == original


def test_benchmark_report_valid() -> None:
    """Test BenchmarkReport with valid data."""
    mtl_result = TranslationResult(
        system_name="mtl",
        line_scores=[
            LineScore(
                line_id="line1",
                source_text="源",
                translation="MTL Trans",
                scores=[
                    RubricScore(
                        dimension=RubricDimension.ACCURACY,
                        score=3,
                        reasoning="OK",
                    )
                ],
            )
        ],
        dimension_aggregates=[
            DimensionAggregate(
                dimension=RubricDimension.ACCURACY,
                mean=3.0,
                median=3.0,
                stddev=0.0,
                min_score=3,
                max_score=3,
            )
        ],
    )
    rentl_result = TranslationResult(
        system_name="rentl",
        line_scores=[
            LineScore(
                line_id="line1",
                source_text="源",
                translation="Rentl Trans",
                scores=[
                    RubricScore(
                        dimension=RubricDimension.ACCURACY,
                        score=5,
                        reasoning="Excellent",
                    )
                ],
            )
        ],
        dimension_aggregates=[
            DimensionAggregate(
                dimension=RubricDimension.ACCURACY,
                mean=5.0,
                median=5.0,
                stddev=0.0,
                min_score=5,
                max_score=5,
            )
        ],
    )
    report = BenchmarkReport(
        eval_set="katawa-shoujo",
        slice_name="demo",
        scoring_mode="reference_based",
        judge_model="gpt-4o",
        mtl_result=mtl_result,
        rentl_result=rentl_result,
    )
    assert report.eval_set == "katawa-shoujo"
    assert report.slice_name == "demo"
    assert report.scoring_mode == "reference_based"
    assert report.judge_model == "gpt-4o"
    assert report.mtl_result.system_name == "mtl"
    assert report.rentl_result.system_name == "rentl"
    assert report.head_to_head is None
    assert report.head_to_head_summary is None


def test_benchmark_report_with_head_to_head() -> None:
    """Test BenchmarkReport with head-to-head data."""
    mtl_result = TranslationResult(
        system_name="mtl",
        line_scores=[],
        dimension_aggregates=[],
    )
    rentl_result = TranslationResult(
        system_name="rentl",
        line_scores=[],
        dimension_aggregates=[],
    )
    head_to_head = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            translation_a="Trans A",
            translation_b="Trans B",
            winner="A",
            reasoning="A is better",
        )
    ]
    summary = HeadToHeadSummary(
        total_comparisons=1,
        system_a_wins=1,
        system_b_wins=0,
        ties=0,
    )
    report = BenchmarkReport(
        eval_set="test",
        scoring_mode="reference_free",
        judge_model="claude-3-5-sonnet-20241022",
        mtl_result=mtl_result,
        rentl_result=rentl_result,
        head_to_head=head_to_head,
        head_to_head_summary=summary,
    )
    assert report.head_to_head is not None
    assert len(report.head_to_head) == 1
    assert report.head_to_head_summary is not None
    assert report.head_to_head_summary.total_comparisons == 1


def test_benchmark_report_roundtrip() -> None:
    """Test BenchmarkReport serialization roundtrip."""
    mtl_result = TranslationResult(
        system_name="mtl",
        line_scores=[],
        dimension_aggregates=[],
    )
    rentl_result = TranslationResult(
        system_name="rentl",
        line_scores=[],
        dimension_aggregates=[],
    )
    original = BenchmarkReport(
        eval_set="test-set",
        slice_name="test-slice",
        scoring_mode="reference_based",
        judge_model="gpt-4o",
        mtl_result=mtl_result,
        rentl_result=rentl_result,
    )
    json_data = original.model_dump()
    reconstructed = BenchmarkReport.model_validate(json_data)
    assert reconstructed == original
