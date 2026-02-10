"""Benchmark report models for aggregated results."""

from pydantic import BaseModel, Field

from rentl_schemas.benchmark.rubric import HeadToHeadResult, RubricDimension


class PairwiseSummary(BaseModel):
    """Summary of head-to-head comparison results for one candidate pair."""

    candidate_a_name: str = Field(
        description="Name of the first candidate in this pairwise comparison"
    )
    candidate_b_name: str = Field(
        description="Name of the second candidate in this pairwise comparison"
    )
    total_comparisons: int = Field(
        description="Total number of head-to-head comparisons performed for this pair"
    )
    candidate_a_wins: int = Field(description="Number of lines where candidate A won")
    candidate_b_wins: int = Field(description="Number of lines where candidate B won")
    ties: int = Field(description="Number of lines judged as a tie")
    dimension_win_rates: dict[RubricDimension, dict[str, float]] = Field(
        default_factory=dict,
        description=(
            "Win rates per rubric dimension, "
            "keyed by dimension then outcome ('A', 'B', 'tie')"
        ),
    )


class EloRating(BaseModel):
    """Elo rating for a single candidate."""

    candidate_name: str = Field(description="Name of the candidate")
    rating: float = Field(description="Elo rating score for this candidate")


class BenchmarkReport(BaseModel):
    """Complete benchmark evaluation report."""

    eval_set: str = Field(description="Name of the evaluation set used")
    slice_name: str | None = Field(
        default=None,
        description="Name of slice evaluated (None if full eval set)",
    )
    judge_model: str = Field(description="Model identifier used for judging")
    candidates: list[str] = Field(
        description="List of candidate names included in this benchmark"
    )
    head_to_head_results: list[HeadToHeadResult] = Field(
        description="All pairwise head-to-head comparison results"
    )
    pairwise_summaries: list[PairwiseSummary] = Field(
        description="Per-pair win rate summaries (one per candidate pair)"
    )
    elo_ratings: list[EloRating] = Field(description="Elo ratings for all candidates")
    overall_ranking: list[str] = Field(
        description="Candidate names ordered by Elo rating (best to worst)"
    )
