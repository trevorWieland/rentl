"""Unit tests for benchmark report schemas and report generation."""

from rentl_core.benchmark.report import (
    BenchmarkReportBuilder,
    format_report_summary,
)
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


# --- BenchmarkReportBuilder Tests ---


def test_build_pairwise_summary_basic() -> None:
    """Test building pairwise summary from head-to-head results."""
    results = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源1",
            candidate_a_name="rentl",
            candidate_b_name="mtl",
            translation_a="Trans A1",
            translation_b="Trans B1",
            winner="A",
            reasoning="A is better",
            dimension_winners={
                RubricDimension.ACCURACY: "A",
                RubricDimension.STYLE_FIDELITY: "B",
                RubricDimension.CONSISTENCY: "tie",
            },
        ),
        HeadToHeadResult(
            line_id="line2",
            source_text="源2",
            candidate_a_name="rentl",
            candidate_b_name="mtl",
            translation_a="Trans A2",
            translation_b="Trans B2",
            winner="B",
            reasoning="B is better",
            dimension_winners={
                RubricDimension.ACCURACY: "B",
                RubricDimension.STYLE_FIDELITY: "A",
                RubricDimension.CONSISTENCY: "A",
            },
        ),
    ]

    summary = BenchmarkReportBuilder.build_pairwise_summary(results, "rentl", "mtl")

    assert summary.candidate_a_name == "rentl"
    assert summary.candidate_b_name == "mtl"
    assert summary.total_comparisons == 2
    assert summary.candidate_a_wins == 1
    assert summary.candidate_b_wins == 1
    assert summary.ties == 0

    # Check dimension win rates
    assert summary.dimension_win_rates[RubricDimension.ACCURACY]["A"] == 0.5
    assert summary.dimension_win_rates[RubricDimension.ACCURACY]["B"] == 0.5
    assert summary.dimension_win_rates[RubricDimension.ACCURACY]["tie"] == 0.0

    assert summary.dimension_win_rates[RubricDimension.STYLE_FIDELITY]["A"] == 0.5
    assert summary.dimension_win_rates[RubricDimension.STYLE_FIDELITY]["B"] == 0.5

    assert summary.dimension_win_rates[RubricDimension.CONSISTENCY]["A"] == 0.5
    assert summary.dimension_win_rates[RubricDimension.CONSISTENCY]["tie"] == 0.5


def test_build_pairwise_summary_with_ties() -> None:
    """Test pairwise summary calculation with ties."""
    results = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源1",
            candidate_a_name="a",
            candidate_b_name="b",
            translation_a="Trans A",
            translation_b="Trans B",
            winner="tie",
            reasoning="Equal",
        ),
        HeadToHeadResult(
            line_id="line2",
            source_text="源2",
            candidate_a_name="a",
            candidate_b_name="b",
            translation_a="Trans A",
            translation_b="Trans B",
            winner="tie",
            reasoning="Equal",
        ),
    ]

    summary = BenchmarkReportBuilder.build_pairwise_summary(results, "a", "b")

    assert summary.candidate_a_wins == 0
    assert summary.candidate_b_wins == 0
    assert summary.ties == 2


def test_build_pairwise_summary_empty_results() -> None:
    """Test pairwise summary with empty results list."""
    summary = BenchmarkReportBuilder.build_pairwise_summary([], "a", "b")

    assert summary.total_comparisons == 0
    assert summary.candidate_a_wins == 0
    assert summary.candidate_b_wins == 0
    assert summary.ties == 0

    # Should handle division by zero gracefully
    for dimension in RubricDimension:
        assert summary.dimension_win_rates[dimension]["A"] == 0.0
        assert summary.dimension_win_rates[dimension]["B"] == 0.0
        assert summary.dimension_win_rates[dimension]["tie"] == 0.0


def test_compute_elo_ratings_basic() -> None:
    """Test Elo rating computation from pairwise summaries."""
    pairwise = [
        PairwiseSummary(
            candidate_a_name="winner",
            candidate_b_name="loser",
            total_comparisons=10,
            candidate_a_wins=8,
            candidate_b_wins=2,
            ties=0,
        )
    ]

    ratings = BenchmarkReportBuilder.compute_elo_ratings(["winner", "loser"], pairwise)

    # Winner should have higher rating than initial
    winner_rating = next(r for r in ratings if r.candidate_name == "winner")
    loser_rating = next(r for r in ratings if r.candidate_name == "loser")

    assert winner_rating.rating > 1500.0
    assert loser_rating.rating < 1500.0


def test_compute_elo_ratings_ties() -> None:
    """Test Elo rating computation with ties."""
    pairwise = [
        PairwiseSummary(
            candidate_a_name="a",
            candidate_b_name="b",
            total_comparisons=10,
            candidate_a_wins=0,
            candidate_b_wins=0,
            ties=10,
        )
    ]

    ratings = BenchmarkReportBuilder.compute_elo_ratings(["a", "b"], pairwise)

    # Both should remain at initial rating with all ties
    a_rating = next(r for r in ratings if r.candidate_name == "a")
    b_rating = next(r for r in ratings if r.candidate_name == "b")

    # Ratings should be very close to initial (small rounding differences allowed)
    assert abs(a_rating.rating - 1500.0) < 1.0
    assert abs(b_rating.rating - 1500.0) < 1.0


def test_compute_elo_ratings_three_way() -> None:
    """Test Elo rating computation with 3 candidates."""
    pairwise = [
        PairwiseSummary(
            candidate_a_name="best",
            candidate_b_name="mid",
            total_comparisons=10,
            candidate_a_wins=8,
            candidate_b_wins=2,
            ties=0,
        ),
        PairwiseSummary(
            candidate_a_name="best",
            candidate_b_name="worst",
            total_comparisons=10,
            candidate_a_wins=10,
            candidate_b_wins=0,
            ties=0,
        ),
        PairwiseSummary(
            candidate_a_name="mid",
            candidate_b_name="worst",
            total_comparisons=10,
            candidate_a_wins=7,
            candidate_b_wins=3,
            ties=0,
        ),
    ]

    ratings = BenchmarkReportBuilder.compute_elo_ratings(
        ["best", "mid", "worst"], pairwise
    )

    best_rating = next(r for r in ratings if r.candidate_name == "best")
    mid_rating = next(r for r in ratings if r.candidate_name == "mid")
    worst_rating = next(r for r in ratings if r.candidate_name == "worst")

    # Should be ordered correctly
    assert best_rating.rating > mid_rating.rating
    assert mid_rating.rating > worst_rating.rating


def test_compute_elo_ratings_zero_comparisons() -> None:
    """Test Elo rating computation handles zero-comparison summaries safely."""
    pairwise = [
        PairwiseSummary(
            candidate_a_name="a",
            candidate_b_name="b",
            total_comparisons=0,
            candidate_a_wins=0,
            candidate_b_wins=0,
            ties=0,
        )
    ]

    # Should not crash on division by zero
    ratings = BenchmarkReportBuilder.compute_elo_ratings(["a", "b"], pairwise)

    # Both should remain at initial rating when no comparisons occurred
    a_rating = next(r for r in ratings if r.candidate_name == "a")
    b_rating = next(r for r in ratings if r.candidate_name == "b")

    assert a_rating.rating == 1500.0
    assert b_rating.rating == 1500.0


def test_build_report() -> None:
    """Test building complete benchmark report."""
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
        EloRating(candidate_name="a", rating=1520.0),
        EloRating(candidate_name="b", rating=1480.0),
    ]

    report = BenchmarkReportBuilder.build_report(
        eval_set="test-set",
        slice_name="test-slice",
        judge_model="gpt-4o",
        candidates=["a", "b"],
        head_to_head_results=head_to_head,
        pairwise_summaries=pairwise,
        elo_ratings=elo_ratings,
    )

    assert report.eval_set == "test-set"
    assert report.slice_name == "test-slice"
    assert report.judge_model == "gpt-4o"
    assert report.candidates == ["a", "b"]
    assert len(report.head_to_head_results) == 1
    assert len(report.pairwise_summaries) == 1
    assert len(report.elo_ratings) == 2
    # Verify overall_ranking is derived from Elo ratings (a has higher rating)
    assert report.overall_ranking == ["a", "b"]


def test_build_report_derives_ranking_from_elo() -> None:
    """Test that build_report derives overall_ranking from Elo ratings."""
    head_to_head = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="worst",
            candidate_b_name="best",
            translation_a="Trans A",
            translation_b="Trans B",
            winner="B",
            reasoning="B wins",
        )
    ]
    pairwise = [
        PairwiseSummary(
            candidate_a_name="worst",
            candidate_b_name="best",
            total_comparisons=10,
            candidate_a_wins=2,
            candidate_b_wins=8,
            ties=0,
        )
    ]
    # Elo ratings provided in arbitrary order
    elo_ratings = [
        EloRating(candidate_name="worst", rating=1450.0),
        EloRating(candidate_name="mid", rating=1500.0),
        EloRating(candidate_name="best", rating=1550.0),
    ]

    report = BenchmarkReportBuilder.build_report(
        eval_set="test-set",
        slice_name=None,
        judge_model="gpt-4o",
        candidates=["worst", "mid", "best"],
        head_to_head_results=head_to_head,
        pairwise_summaries=pairwise,
        elo_ratings=elo_ratings,
    )

    # Verify overall_ranking is derived from Elo ratings (best to worst)
    assert report.overall_ranking == ["best", "mid", "worst"]


def test_format_report_summary_basic() -> None:
    """Test formatting report as human-readable summary."""
    head_to_head = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="rentl",
            candidate_b_name="mtl",
            translation_a="Trans A",
            translation_b="Trans B",
            winner="A",
            reasoning="A wins",
        )
    ]
    pairwise = [
        PairwiseSummary(
            candidate_a_name="rentl",
            candidate_b_name="mtl",
            total_comparisons=10,
            candidate_a_wins=7,
            candidate_b_wins=2,
            ties=1,
            dimension_win_rates={
                RubricDimension.ACCURACY: {"A": 0.7, "B": 0.2, "tie": 0.1},
                RubricDimension.STYLE_FIDELITY: {"A": 0.6, "B": 0.3, "tie": 0.1},
            },
        )
    ]
    elo_ratings = [
        EloRating(candidate_name="rentl", rating=1542.3),
        EloRating(candidate_name="mtl", rating=1457.7),
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

    summary = format_report_summary(report)

    # Check key parts are present
    assert "=== Benchmark Report: katawa-shoujo ===" in summary
    assert "Slice: demo" in summary
    assert "Judge Model: gpt-4o" in summary
    assert "rentl" in summary
    assert "mtl" in summary
    assert "Elo 1542.3" in summary
    assert "Elo 1457.7" in summary
    assert "7 wins" in summary
    assert "2 wins" in summary
    assert "Ties: 1" in summary
    assert "accuracy" in summary
    assert "style_fidelity" in summary


def test_format_report_summary_no_slice() -> None:
    """Test formatting report with no slice."""
    head_to_head = [
        HeadToHeadResult(
            line_id="line1",
            source_text="源",
            candidate_a_name="a",
            candidate_b_name="b",
            translation_a="Trans A",
            translation_b="Trans B",
            winner="tie",
            reasoning="Equal",
        )
    ]
    pairwise = [
        PairwiseSummary(
            candidate_a_name="a",
            candidate_b_name="b",
            total_comparisons=1,
            candidate_a_wins=0,
            candidate_b_wins=0,
            ties=1,
        )
    ]
    elo_ratings = [
        EloRating(candidate_name="a", rating=1500.0),
        EloRating(candidate_name="b", rating=1500.0),
    ]
    report = BenchmarkReport(
        eval_set="test-set",
        slice_name=None,
        judge_model="gpt-4o",
        candidates=["a", "b"],
        head_to_head_results=head_to_head,
        pairwise_summaries=pairwise,
        elo_ratings=elo_ratings,
        overall_ranking=["a", "b"],
    )

    summary = format_report_summary(report)

    # Should not include slice line
    assert "Slice:" not in summary
    assert "=== Benchmark Report: test-set ===" in summary
