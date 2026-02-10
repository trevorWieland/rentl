"""Benchmark report generation with aggregation and formatting.

Assembles pairwise head-to-head results into aggregated reports with
win rates, Elo ratings, and human-readable output for CLI display.
"""

from rentl_schemas.benchmark.report import (
    BenchmarkReport,
    EloRating,
    PairwiseSummary,
)
from rentl_schemas.benchmark.rubric import (
    HeadToHeadResult,
    RubricDimension,
)


class BenchmarkReportBuilder:
    """Build aggregated benchmark reports from head-to-head results."""

    @staticmethod
    def build_pairwise_summary(
        head_to_head_results: list[HeadToHeadResult],
        candidate_a_name: str,
        candidate_b_name: str,
    ) -> PairwiseSummary:
        """Build pairwise summary from head-to-head results for one candidate pair.

        Args:
            head_to_head_results: Per-line head-to-head results for this pair
            candidate_a_name: Name of first candidate
            candidate_b_name: Name of second candidate

        Returns:
            Aggregated pairwise summary with win rates
        """
        total = len(head_to_head_results)
        candidate_a_wins = sum(
            1 for result in head_to_head_results if result.winner == "A"
        )
        candidate_b_wins = sum(
            1 for result in head_to_head_results if result.winner == "B"
        )
        ties = sum(1 for result in head_to_head_results if result.winner == "tie")

        # Calculate per-dimension win rates
        dimension_win_rates: dict[RubricDimension, dict[str, float]] = {}

        for dimension in RubricDimension:
            dim_a_wins = 0
            dim_b_wins = 0
            dim_ties = 0

            for result in head_to_head_results:
                winner = result.dimension_winners.get(dimension)
                if winner == "A":
                    dim_a_wins += 1
                elif winner == "B":
                    dim_b_wins += 1
                elif winner == "tie":
                    dim_ties += 1

            dimension_win_rates[dimension] = {
                "A": dim_a_wins / total if total > 0 else 0.0,
                "B": dim_b_wins / total if total > 0 else 0.0,
                "tie": dim_ties / total if total > 0 else 0.0,
            }

        return PairwiseSummary(
            candidate_a_name=candidate_a_name,
            candidate_b_name=candidate_b_name,
            total_comparisons=total,
            candidate_a_wins=candidate_a_wins,
            candidate_b_wins=candidate_b_wins,
            ties=ties,
            dimension_win_rates=dimension_win_rates,
        )

    @staticmethod
    def compute_elo_ratings(
        candidates: list[str],
        pairwise_summaries: list[PairwiseSummary],
        k_factor: float = 32.0,
        initial_rating: float = 1500.0,
    ) -> list[EloRating]:
        """Compute Elo ratings from pairwise comparison results.

        Args:
            candidates: List of candidate names
            pairwise_summaries: All pairwise comparison summaries
            k_factor: Elo K-factor (sensitivity to individual games)
            initial_rating: Starting Elo rating for all candidates

        Returns:
            List of Elo ratings for all candidates
        """
        # Initialize ratings
        ratings: dict[str, float] = dict.fromkeys(candidates, initial_rating)

        # Process each pairwise summary
        for summary in pairwise_summaries:
            # Skip pairs with no comparisons
            if summary.total_comparisons == 0:
                continue

            # Expected score for A vs B
            expected_a = 1 / (
                1
                + 10
                ** (
                    (
                        ratings[summary.candidate_b_name]
                        - ratings[summary.candidate_a_name]
                    )
                    / 400
                )
            )

            # Actual score (wins + 0.5 * ties) / total
            actual_a = (
                summary.candidate_a_wins + 0.5 * summary.ties
            ) / summary.total_comparisons

            # Update ratings
            ratings[summary.candidate_a_name] += k_factor * (actual_a - expected_a)
            ratings[summary.candidate_b_name] += k_factor * (
                (1 - actual_a) - (1 - expected_a)
            )

        return [
            EloRating(candidate_name=name, rating=ratings[name]) for name in candidates
        ]

    @staticmethod
    def build_report(
        eval_set: str,
        slice_name: str | None,
        judge_model: str,
        candidates: list[str],
        head_to_head_results: list[HeadToHeadResult],
        pairwise_summaries: list[PairwiseSummary],
        elo_ratings: list[EloRating],
    ) -> BenchmarkReport:
        """Build complete benchmark report.

        Args:
            eval_set: Evaluation set name
            slice_name: Slice name (None if full set)
            judge_model: Judge model identifier
            candidates: List of candidate names
            head_to_head_results: All pairwise head-to-head results
            pairwise_summaries: Per-pair win rate summaries
            elo_ratings: Elo ratings for all candidates

        Returns:
            Complete benchmark report with overall_ranking derived from Elo ratings
        """
        # Derive overall_ranking from Elo ratings (best to worst)
        overall_ranking = [
            rating.candidate_name
            for rating in sorted(elo_ratings, key=lambda r: r.rating, reverse=True)
        ]

        return BenchmarkReport(
            eval_set=eval_set,
            slice_name=slice_name,
            judge_model=judge_model,
            candidates=candidates,
            head_to_head_results=head_to_head_results,
            pairwise_summaries=pairwise_summaries,
            elo_ratings=elo_ratings,
            overall_ranking=overall_ranking,
        )


def format_report_summary(report: BenchmarkReport) -> str:
    """Format benchmark report as human-readable summary text.

    Args:
        report: Benchmark report to format

    Returns:
        Formatted summary string for CLI output
    """
    lines = [
        f"=== Benchmark Report: {report.eval_set} ===",
    ]
    if report.slice_name:
        lines.append(f"Slice: {report.slice_name}")
    lines.extend([
        f"Judge Model: {report.judge_model}",
        f"Candidates: {', '.join(report.candidates)}",
        "",
        "--- Overall Ranking (by Elo) ---",
    ])

    # Show Elo ratings in ranking order
    elo_map = {rating.candidate_name: rating.rating for rating in report.elo_ratings}
    for rank, candidate in enumerate(report.overall_ranking, 1):
        elo = elo_map.get(candidate, 0.0)
        lines.append(f"{rank}. {candidate}: Elo {elo:.1f}")

    lines.extend(("", "--- Pairwise Win Rates ---"))

    # Show each pairwise comparison
    for summary in report.pairwise_summaries:
        total = summary.total_comparisons
        a_pct = summary.candidate_a_wins / total * 100 if total > 0 else 0.0
        b_pct = summary.candidate_b_wins / total * 100 if total > 0 else 0.0
        tie_pct = summary.ties / total * 100 if total > 0 else 0.0

        a_wins_str = f"  {summary.candidate_a_name}: "
        a_wins_str += f"{summary.candidate_a_wins} wins ({a_pct:.1f}%)"
        b_wins_str = f"  {summary.candidate_b_name}: "
        b_wins_str += f"{summary.candidate_b_wins} wins ({b_pct:.1f}%)"

        lines.extend([
            "",
            f"{summary.candidate_a_name} vs {summary.candidate_b_name}:",
            a_wins_str,
            b_wins_str,
            f"  Ties: {summary.ties} ({tie_pct:.1f}%)",
        ])

        # Show per-dimension win rates
        lines.append("  Per-dimension:")
        for dimension, rates in summary.dimension_win_rates.items():
            lines.append(
                f"    {dimension.value}: "
                f"{summary.candidate_a_name}={rates['A'] * 100:.1f}%, "
                f"{summary.candidate_b_name}={rates['B'] * 100:.1f}%, "
                f"tie={rates['tie'] * 100:.1f}%"
            )

    return "\n".join(lines)
