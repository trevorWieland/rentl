"""Unit tests for rubric and scoring schemas."""

import pytest
from pydantic import ValidationError

from rentl_schemas.benchmark.rubric import HeadToHeadResult, RubricDimension


def test_rubric_dimension_enum() -> None:
    """Test RubricDimension enum values."""
    assert RubricDimension.ACCURACY == "accuracy"
    assert RubricDimension.STYLE_FIDELITY == "style_fidelity"
    assert RubricDimension.CONSISTENCY == "consistency"


def test_head_to_head_result_valid() -> None:
    """Test HeadToHeadResult with valid data."""
    result = HeadToHeadResult(
        line_id="scene_1",
        source_text="ありがとう",
        candidate_a_name="rentl",
        candidate_b_name="mtl",
        translation_a="Thank you",
        translation_b="Thanks",
        winner="A",
        reasoning="Translation A is more formal and appropriate for the context.",
        dimension_winners={
            RubricDimension.ACCURACY: "tie",
            RubricDimension.STYLE_FIDELITY: "A",
            RubricDimension.CONSISTENCY: "A",
        },
        presented_as_a="rentl",
    )
    assert result.line_id == "scene_1"
    assert result.candidate_a_name == "rentl"
    assert result.candidate_b_name == "mtl"
    assert result.winner == "A"
    assert len(result.dimension_winners) == 3
    assert result.presented_as_a == "rentl"


def test_head_to_head_result_tie() -> None:
    """Test HeadToHeadResult with tie winner."""
    result = HeadToHeadResult(
        line_id="line_1",
        source_text="テスト",
        candidate_a_name="system1",
        candidate_b_name="system2",
        translation_a="Test",
        translation_b="Testing",
        winner="tie",
        reasoning="Both translations are equally valid.",
        presented_as_a="system1",
    )
    assert result.winner == "tie"


def test_head_to_head_result_winner_validation() -> None:
    """Test HeadToHeadResult validates winner values."""
    # Valid winners
    for winner in ["A", "B", "tie"]:
        result = HeadToHeadResult(
            line_id="line_1",
            source_text="源",
            candidate_a_name="sys1",
            candidate_b_name="sys2",
            translation_a="Source",
            translation_b="Origin",
            winner=winner,  # type: ignore[arg-type]
            reasoning="Test",
            presented_as_a="sys1",
        )
        assert result.winner == winner

    # Invalid winner
    with pytest.raises(ValidationError):
        HeadToHeadResult(
            line_id="line_1",
            source_text="源",
            candidate_a_name="sys1",
            candidate_b_name="sys2",
            translation_a="Source",
            translation_b="Origin",
            winner="C",  # type: ignore[arg-type]
            reasoning="Test",
            presented_as_a="sys1",
        )


def test_head_to_head_result_no_dimension_winners() -> None:
    """Test HeadToHeadResult with default empty dimension_winners."""
    result = HeadToHeadResult(
        line_id="line_1",
        source_text="テスト",
        candidate_a_name="candidate_a",
        candidate_b_name="candidate_b",
        translation_a="Test",
        translation_b="Testing",
        winner="A",
        reasoning="A is better",
        presented_as_a="candidate_a",
    )
    assert result.dimension_winners == {}


def test_head_to_head_result_roundtrip() -> None:
    """Test HeadToHeadResult serialization roundtrip."""
    original = HeadToHeadResult(
        line_id="line_1",
        source_text="源",
        candidate_a_name="rentl-full",
        candidate_b_name="mtl",
        translation_a="Source",
        translation_b="Origin",
        winner="B",
        reasoning="B is more idiomatic",
        dimension_winners={
            RubricDimension.ACCURACY: "tie",
            RubricDimension.STYLE_FIDELITY: "B",
        },
        presented_as_a="rentl-full",
    )
    json_data = original.model_dump()
    reconstructed = HeadToHeadResult.model_validate(json_data)
    assert reconstructed == original


def test_head_to_head_result_candidate_names() -> None:
    """Test HeadToHeadResult includes candidate names for N-way tracking."""
    result = HeadToHeadResult(
        line_id="line_1",
        source_text="源",
        candidate_a_name="gpt4-full",
        candidate_b_name="claude-minimal",
        translation_a="Translation A",
        translation_b="Translation B",
        winner="A",
        reasoning="A preserves context better",
        presented_as_a="gpt4-full",
    )
    assert result.candidate_a_name == "gpt4-full"
    assert result.candidate_b_name == "claude-minimal"
    assert result.presented_as_a == "gpt4-full"


def test_head_to_head_result_presentation_order() -> None:
    """Test presented_as_a records which candidate was shown as 'A' to judge."""
    # Scenario: candidate_b was presented as "Translation A" to the judge
    result = HeadToHeadResult(
        line_id="line_1",
        source_text="源",
        candidate_a_name="rentl",
        candidate_b_name="mtl",
        translation_a="Source",
        translation_b="Origin",
        winner="A",  # Winner is "A" in canonical order
        # Judge's reasoning uses presentation-order labels
        reasoning="Translation A was clearly superior in accuracy.",
        presented_as_a="mtl",  # But "A" in judge's view was actually mtl
    )
    # With presented_as_a="mtl", we know that when the judge says "Translation A",
    # they're referring to the mtl candidate (even though winner="A" means rentl won)
    assert result.presented_as_a == "mtl"
    assert result.winner == "A"
    assert result.candidate_a_name == "rentl"
