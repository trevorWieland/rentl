"""Rubric and scoring models for LLM judge evaluation."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class RubricDimension(StrEnum):
    """Dimensions on which translations are scored."""

    ACCURACY = "accuracy"
    STYLE_FIDELITY = "style_fidelity"
    CONSISTENCY = "consistency"


class RubricScore(BaseModel):
    """A single rubric dimension score with reasoning."""

    dimension: RubricDimension = Field(
        description="Which rubric dimension this score evaluates"
    )
    score: int = Field(
        ge=1,
        le=5,
        description="Score from 1 (poor) to 5 (excellent) for this dimension",
    )
    reasoning: str = Field(
        description="Judge's explanation for why this score was assigned"
    )


class LineScore(BaseModel):
    """Scores for a single line across all rubric dimensions."""

    line_id: str = Field(description="Unique identifier for the evaluated line")
    source_text: str = Field(description="Original source language text")
    translation: str = Field(description="The translation being scored")
    reference: str | None = Field(
        default=None,
        description="Reference translation (if available and used for scoring)",
    )
    scores: list[RubricScore] = Field(description="Scores for each rubric dimension")


class HeadToHeadResult(BaseModel):
    """Result of a head-to-head comparison between two translations."""

    line_id: str = Field(description="Unique identifier for the evaluated line")
    source_text: str = Field(description="Original source language text")
    translation_a: str = Field(description="First translation (randomized assignment)")
    translation_b: str = Field(description="Second translation (randomized assignment)")
    winner: Literal["A", "B", "tie"] = Field(
        description="Which translation won this comparison"
    )
    reasoning: str = Field(description="Judge's explanation for the winner selection")
    dimension_winners: dict[RubricDimension, Literal["A", "B", "tie"]] = Field(
        default_factory=dict,
        description="Winner per rubric dimension (optional per-dimension breakdown)",
    )
