"""Unit tests for benchmark report schemas."""

from rentl_schemas.benchmark.report import (
    BenchmarkReport,
    EloRating,
    PairwiseSummary,
)
from rentl_schemas.benchmark.rubric import HeadToHeadResult, RubricDimension


def test_pairwise_summary_valid() -> None:
    """Test PairwiseSummary with valid data."""
    summary = PairwiseSummary(
        candidate_a_name="rentl",
        candidate_b_name="mtl",
        total_comparisons=100,
        candidate_a_wins=45,
        candidate_b_wins=40,
        ties=15,
        dimension_win_rates={
            RubricDimension.ACCURACY: {"A": 0.50, "B": 0.35, "tie": 0.15},
            RubricDimension.STYLE_FIDELITY: {"A": 0.40, "B": 0.45, "tie": 0.15},
        },
    )
    assert summary.candidate_a_name == "rentl"
    assert summary.candidate_b_name == "mtl"
    assert summary.total_comparisons == 100
    assert summary.candidate_a_wins == 45
    assert summary.candidate_b_wins == 40
    assert summary.ties == 15
    assert len(summary.dimension_win_rates) == 2


def test_pairwise_summary_no_dimension_rates() -> None:
    """Test PairwiseSummary with default empty dimension_win_rates."""
    summary = PairwiseSummary(
        candidate_a_name="sys1",
        candidate_b_name="sys2",
        total_comparisons=50,
        candidate_a_wins=25,
        candidate_b_wins=20,
        ties=5,
    )
    assert summary.dimension_win_rates == {}


def test_pairwise_summary_roundtrip() -> None:
    """Test PairwiseSummary serialization roundtrip."""
    original = PairwiseSummary(
        candidate_a_name="candidate_x",
        candidate_b_name="candidate_y",
        total_comparisons=10,
        candidate_a_wins=5,
        candidate_b_wins=4,
        ties=1,
        dimension_win_rates={
            RubricDimension.CONSISTENCY: {"A": 0.6, "B": 0.3, "tie": 0.1},
        },
    )
    json_data = original.model_dump()
    reconstructed = PairwiseSummary.model_validate(json_data)
    assert reconstructed == original


def test_elo_rating_valid() -> None:
    """Test EloRating with valid data."""
    rating = EloRating(candidate_name="rentl", rating=1542.3)
    assert rating.candidate_name == "rentl"
    assert rating.rating == 1542.3


def test_elo_rating_roundtrip() -> None:
    """Test EloRating serialization roundtrip."""
    original = EloRating(candidate_name="mtl", rating=1398.7)
    json_data = original.model_dump()
    reconstructed = EloRating.model_validate(json_data)
    assert reconstructed == original


def test_benchmark_report_valid() -> None:
    """Test BenchmarkReport with valid N-way comparison data."""
    head_to_head = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="rentl",
            candidate_b_name="mtl",
            translation_a="Rentl Trans",
            translation_b="MTL Trans",
            winner="A",
            reasoning="A is better",
        )
    ]
    pairwise = [
        PairwiseSummary(
            candidate_a_name="rentl",
            candidate_b_name="mtl",
            total_comparisons=1,
            candidate_a_wins=1,
            candidate_b_wins=0,
            ties=0,
        )
    ]
    elo_ratings = [
        EloRating(candidate_name="rentl", rating=1520.0),
        EloRating(candidate_name="mtl", rating=1480.0),
    ]
    report = BenchmarkReport(
        eval_set="katawa-shoujo",
        slice_name="demo",
        judge_model="gpt-4o",
        candidates=["rentl", "mtl"],
        head_to_head_results=head_to_head,
        pairwise_summaries=pairwise,
        elo_ratings=elo_ratings,
        overall_ranking=["rentl", "mtl"],
    )
    assert report.eval_set == "katawa-shoujo"
    assert report.slice_name == "demo"
    assert report.judge_model == "gpt-4o"
    assert len(report.candidates) == 2
    assert len(report.head_to_head_results) == 1
    assert len(report.pairwise_summaries) == 1
    assert len(report.elo_ratings) == 2
    assert report.overall_ranking == ["rentl", "mtl"]


def test_benchmark_report_multiple_candidates() -> None:
    """Test BenchmarkReport with more than 2 candidates (N-way)."""
    head_to_head = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="rentl",
            candidate_b_name="mtl",
            translation_a="Trans A",
            translation_b="Trans B",
            winner="A",
            reasoning="A is better",
        ),
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="rentl",
            candidate_b_name="gpt4",
            translation_a="Trans A",
            translation_b="Trans C",
            winner="B",
            reasoning="B is better",
        ),
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="mtl",
            candidate_b_name="gpt4",
            translation_a="Trans B",
            translation_b="Trans C",
            winner="B",
            reasoning="B is better",
        ),
    ]
    pairwise = [
        PairwiseSummary(
            candidate_a_name="rentl",
            candidate_b_name="mtl",
            total_comparisons=1,
            candidate_a_wins=1,
            candidate_b_wins=0,
            ties=0,
        ),
        PairwiseSummary(
            candidate_a_name="rentl",
            candidate_b_name="gpt4",
            total_comparisons=1,
            candidate_a_wins=0,
            candidate_b_wins=1,
            ties=0,
        ),
        PairwiseSummary(
            candidate_a_name="mtl",
            candidate_b_name="gpt4",
            total_comparisons=1,
            candidate_a_wins=0,
            candidate_b_wins=1,
            ties=0,
        ),
    ]
    elo_ratings = [
        EloRating(candidate_name="gpt4", rating=1550.0),
        EloRating(candidate_name="rentl", rating=1500.0),
        EloRating(candidate_name="mtl", rating=1450.0),
    ]
    report = BenchmarkReport(
        eval_set="test",
        slice_name=None,
        judge_model="claude-3-5-sonnet-20241022",
        candidates=["rentl", "mtl", "gpt4"],
        head_to_head_results=head_to_head,
        pairwise_summaries=pairwise,
        elo_ratings=elo_ratings,
        overall_ranking=["gpt4", "rentl", "mtl"],
    )
    assert len(report.candidates) == 3
    assert len(report.head_to_head_results) == 3  # 3 pairs for 3 candidates
    assert len(report.pairwise_summaries) == 3
    assert len(report.elo_ratings) == 3
    assert report.overall_ranking[0] == "gpt4"


def test_benchmark_report_roundtrip() -> None:
    """Test BenchmarkReport serialization roundtrip."""
    head_to_head = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="a",
            candidate_b_name="b",
            translation_a="Trans A",
            translation_b="Trans B",
            winner="A",
            reasoning="A wins",
        )
    ]
    pairwise = [
        PairwiseSummary(
            candidate_a_name="a",
            candidate_b_name="b",
            total_comparisons=1,
            candidate_a_wins=1,
            candidate_b_wins=0,
            ties=0,
        )
    ]
    elo_ratings = [
        EloRating(candidate_name="a", rating=1510.0),
        EloRating(candidate_name="b", rating=1490.0),
    ]
    original = BenchmarkReport(
        eval_set="test-set",
        slice_name="test-slice",
        judge_model="gpt-4o",
        candidates=["a", "b"],
        head_to_head_results=head_to_head,
        pairwise_summaries=pairwise,
        elo_ratings=elo_ratings,
        overall_ranking=["a", "b"],
    )
    json_data = original.model_dump()
    reconstructed = BenchmarkReport.model_validate(json_data)
    assert reconstructed == original


def test_benchmark_report_no_slice() -> None:
    """Test BenchmarkReport with no slice specified."""
    head_to_head = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="sys1",
            candidate_b_name="sys2",
            translation_a="Trans 1",
            translation_b="Trans 2",
            winner="tie",
            reasoning="Equal quality",
        )
    ]
    pairwise = [
        PairwiseSummary(
            candidate_a_name="sys1",
            candidate_b_name="sys2",
            total_comparisons=1,
            candidate_a_wins=0,
            candidate_b_wins=0,
            ties=1,
        )
    ]
    elo_ratings = [
        EloRating(candidate_name="sys1", rating=1500.0),
        EloRating(candidate_name="sys2", rating=1500.0),
    ]
    report = BenchmarkReport(
        eval_set="full-set",
        slice_name=None,
        judge_model="gpt-4o",
        candidates=["sys1", "sys2"],
        head_to_head_results=head_to_head,
        pairwise_summaries=pairwise,
        elo_ratings=elo_ratings,
        overall_ranking=["sys1", "sys2"],
    )
    assert report.slice_name is None
