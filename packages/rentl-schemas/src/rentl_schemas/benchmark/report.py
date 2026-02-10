"""Benchmark report models for aggregated results."""

from pydantic import BaseModel, Field

from rentl_schemas.benchmark.rubric import (
    HeadToHeadResult,
    LineScore,
    RubricDimension,
)


class DimensionAggregate(BaseModel):
    """Aggregated statistics for a single rubric dimension."""

    dimension: RubricDimension = Field(
        description="Which rubric dimension these statistics describe"
    )
    mean: float = Field(description="Mean score across all lines for this dimension")
    median: float = Field(
        description="Median score across all lines for this dimension"
    )
    stddev: float = Field(description="Standard deviation of scores for this dimension")
    min_score: int = Field(
        ge=1,
        le=5,
        description="Minimum score observed for this dimension",
    )
    max_score: int = Field(
        ge=1,
        le=5,
        description="Maximum score observed for this dimension",
    )


class TranslationResult(BaseModel):
    """Results for a single translation system."""

    system_name: str = Field(
        description="Name of the translation system (e.g., 'rentl', 'mtl')"
    )
    line_scores: list[LineScore] = Field(
        description="Per-line scores with reasoning for all evaluated lines"
    )
    dimension_aggregates: list[DimensionAggregate] = Field(
        description="Aggregated statistics per rubric dimension"
    )


class HeadToHeadSummary(BaseModel):
    """Summary of head-to-head comparison results."""

    total_comparisons: int = Field(
        description="Total number of head-to-head comparisons performed"
    )
    system_a_wins: int = Field(description="Number of lines where system A won")
    system_b_wins: int = Field(description="Number of lines where system B won")
    ties: int = Field(description="Number of lines judged as a tie")
    dimension_win_rates: dict[RubricDimension, dict[str, float]] = Field(
        default_factory=dict,
        description=(
            "Win rates per rubric dimension, "
            "keyed by dimension then outcome ('A', 'B', 'tie')"
        ),
    )


class BenchmarkReport(BaseModel):
    """Complete benchmark evaluation report."""

    eval_set: str = Field(description="Name of the evaluation set used")
    slice_name: str | None = Field(
        default=None,
        description="Name of slice evaluated (None if full eval set)",
    )
    scoring_mode: str = Field(
        description="Scoring mode used (reference_based or reference_free)"
    )
    judge_model: str = Field(description="Model identifier used for judging")
    mtl_result: TranslationResult = Field(
        description="Results for the MTL baseline system"
    )
    rentl_result: TranslationResult = Field(
        description="Results for the rentl pipeline system"
    )
    head_to_head: list[HeadToHeadResult] | None = Field(
        default=None,
        description="Head-to-head comparison results (if head-to-head mode was used)",
    )
    head_to_head_summary: HeadToHeadSummary | None = Field(
        default=None,
        description="Summary of head-to-head results (if head-to-head mode was used)",
    )
