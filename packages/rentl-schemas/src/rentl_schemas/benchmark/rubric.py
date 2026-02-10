"""Rubric and scoring models for LLM judge evaluation."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class RubricDimension(StrEnum):
    """Dimensions on which translations are scored."""

    ACCURACY = "accuracy"
    STYLE_FIDELITY = "style_fidelity"
    CONSISTENCY = "consistency"


class HeadToHeadResult(BaseModel):
    """Result of a head-to-head comparison between two translations."""

    line_id: str = Field(description="Unique identifier for the evaluated line")
    source_text: str = Field(description="Original source language text")
    candidate_a_name: str = Field(
        description="Name of the first candidate (before randomization)"
    )
    candidate_b_name: str = Field(
        description="Name of the second candidate (before randomization)"
    )
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
