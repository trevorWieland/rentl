"""Benchmark report generation with aggregation and formatting.

Assembles per-line scores into aggregated reports with statistics and
human-readable output for CLI display.
"""

import statistics

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
)


class BenchmarkReportBuilder:
    """Build aggregated benchmark reports from per-line scores."""

    @staticmethod
    def build_dimension_aggregate(
        dimension: RubricDimension,
        line_scores: list[LineScore],
    ) -> DimensionAggregate:
        """Aggregate scores for a single rubric dimension.

        Args:
            dimension: Which rubric dimension to aggregate
            line_scores: All line scores to aggregate

        Returns:
            Aggregated statistics for the dimension
        """
        scores = []
        for line_score in line_scores:
            # Find the score for this dimension
            for rubric_score in line_score.scores:
                if rubric_score.dimension == dimension:
                    scores.append(rubric_score.score)
                    break

        if not scores:
            # No scores found for this dimension
            return DimensionAggregate(
                dimension=dimension,
                mean=0.0,
                median=0.0,
                stddev=0.0,
                min_score=1,
                max_score=1,
            )

        return DimensionAggregate(
            dimension=dimension,
            mean=statistics.mean(scores),
            median=statistics.median(scores),
            stddev=statistics.stdev(scores) if len(scores) > 1 else 0.0,
            min_score=min(scores),
            max_score=max(scores),
        )

    @staticmethod
    def build_translation_result(
        system_name: str,
        line_scores: list[LineScore],
    ) -> TranslationResult:
        """Build translation result with aggregates for one system.

        Args:
            system_name: Name of the translation system (e.g., "mtl", "rentl")
            line_scores: Per-line scores for this system

        Returns:
            Complete translation result with aggregates
        """
        dimension_aggregates = [
            BenchmarkReportBuilder.build_dimension_aggregate(dim, line_scores)
            for dim in RubricDimension
        ]

        return TranslationResult(
            system_name=system_name,
            line_scores=line_scores,
            dimension_aggregates=dimension_aggregates,
        )

    @staticmethod
    def build_head_to_head_summary(
        head_to_head_results: list[HeadToHeadResult],
        system_a_name: str,
        system_b_name: str,
    ) -> HeadToHeadSummary:
        """Build head-to-head comparison summary.

        Args:
            head_to_head_results: Per-line head-to-head results
            system_a_name: Name of system A
            system_b_name: Name of system B

        Returns:
            Aggregated head-to-head summary with win rates
        """
        total = len(head_to_head_results)
        # Schema uses "A"/"B"/"tie" for winner slots, not system names
        system_a_wins = sum(
            1 for result in head_to_head_results if result.winner == "A"
        )
        system_b_wins = sum(
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
                # Schema uses "A"/"B"/"tie" for winner slots, not system names
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

        return HeadToHeadSummary(
            total_comparisons=total,
            system_a_wins=system_a_wins,
            system_b_wins=system_b_wins,
            ties=ties,
            dimension_win_rates=dimension_win_rates,
        )

    @staticmethod
    def build_report(
        eval_set: str,
        slice_name: str | None,
        scoring_mode: str,
        judge_model: str,
        mtl_line_scores: list[LineScore],
        rentl_line_scores: list[LineScore],
        head_to_head_results: list[HeadToHeadResult] | None = None,
    ) -> BenchmarkReport:
        """Build complete benchmark report.

        Args:
            eval_set: Evaluation set name
            slice_name: Slice name (None if full set)
            scoring_mode: Scoring mode used
            judge_model: Judge model identifier
            mtl_line_scores: Per-line scores for MTL baseline
            rentl_line_scores: Per-line scores for rentl pipeline
            head_to_head_results: Optional head-to-head results

        Returns:
            Complete benchmark report
        """
        mtl_result = BenchmarkReportBuilder.build_translation_result(
            "mtl", mtl_line_scores
        )
        rentl_result = BenchmarkReportBuilder.build_translation_result(
            "rentl", rentl_line_scores
        )

        head_to_head_summary = None
        if head_to_head_results:
            head_to_head_summary = BenchmarkReportBuilder.build_head_to_head_summary(
                head_to_head_results, "mtl", "rentl"
            )

        return BenchmarkReport(
            eval_set=eval_set,
            slice_name=slice_name,
            scoring_mode=scoring_mode,
            judge_model=judge_model,
            mtl_result=mtl_result,
            rentl_result=rentl_result,
            head_to_head=head_to_head_results,
            head_to_head_summary=head_to_head_summary,
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
        f"Scoring Mode: {report.scoring_mode}",
        f"Judge Model: {report.judge_model}",
        "",
        "--- MTL Baseline ---",
    ])
    for agg in report.mtl_result.dimension_aggregates:
        lines.append(
            f"{agg.dimension.value}: "
            f"mean={agg.mean:.2f}, "
            f"median={agg.median:.1f}, "
            f"stddev={agg.stddev:.2f}"
        )
    lines.extend(["", "--- rentl Pipeline ---"])
    for agg in report.rentl_result.dimension_aggregates:
        lines.append(
            f"{agg.dimension.value}: "
            f"mean={agg.mean:.2f}, "
            f"median={agg.median:.1f}, "
            f"stddev={agg.stddev:.2f}"
        )
    lines.append("")

    # Head-to-head summary
    if report.head_to_head_summary:
        summary = report.head_to_head_summary
        lines.extend([
            "--- Head-to-Head Comparison ---",
            f"Total comparisons: {summary.total_comparisons}",
            (
                f"MTL wins: {summary.system_a_wins} "
                f"({summary.system_a_wins / summary.total_comparisons * 100:.1f}%)"
            ),
            (
                f"rentl wins: {summary.system_b_wins} "
                f"({summary.system_b_wins / summary.total_comparisons * 100:.1f}%)"
            ),
            (
                f"Ties: {summary.ties} "
                f"({summary.ties / summary.total_comparisons * 100:.1f}%)"
            ),
            "",
            "Per-dimension win rates:",
        ])
        for dimension, rates in summary.dimension_win_rates.items():
            lines.append(
                f"  {dimension.value}: "
                f"MTL={rates['A'] * 100:.1f}%, "
                f"rentl={rates['B'] * 100:.1f}%, "
                f"tie={rates['tie'] * 100:.1f}%"
            )

    return "\n".join(lines)
