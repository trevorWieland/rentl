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
        line_id="scene1_line10",
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
    )
    assert result.line_id == "scene1_line10"
    assert result.candidate_a_name == "rentl"
    assert result.candidate_b_name == "mtl"
    assert result.winner == "A"
    assert len(result.dimension_winners) == 3


def test_head_to_head_result_tie() -> None:
    """Test HeadToHeadResult with tie winner."""
    result = HeadToHeadResult(
        line_id="test_line",
        source_text="テスト",
        candidate_a_name="system1",
        candidate_b_name="system2",
        translation_a="Test",
        translation_b="Testing",
        winner="tie",
        reasoning="Both translations are equally valid.",
    )
    assert result.winner == "tie"


def test_head_to_head_result_winner_validation() -> None:
    """Test HeadToHeadResult validates winner values."""
    # Valid winners
    for winner in ["A", "B", "tie"]:
        result = HeadToHeadResult(
            line_id="test",
            source_text="源",
            candidate_a_name="sys1",
            candidate_b_name="sys2",
            translation_a="Source",
            translation_b="Origin",
            winner=winner,  # type: ignore[arg-type]
            reasoning="Test",
        )
        assert result.winner == winner

    # Invalid winner
    with pytest.raises(ValidationError):
        HeadToHeadResult(
            line_id="test",
            source_text="源",
            candidate_a_name="sys1",
            candidate_b_name="sys2",
            translation_a="Source",
            translation_b="Origin",
            winner="C",  # type: ignore[arg-type]
            reasoning="Test",
        )


def test_head_to_head_result_no_dimension_winners() -> None:
    """Test HeadToHeadResult with default empty dimension_winners."""
    result = HeadToHeadResult(
        line_id="test",
        source_text="テスト",
        candidate_a_name="candidate_a",
        candidate_b_name="candidate_b",
        translation_a="Test",
        translation_b="Testing",
        winner="A",
        reasoning="A is better",
    )
    assert result.dimension_winners == {}


def test_head_to_head_result_roundtrip() -> None:
    """Test HeadToHeadResult serialization roundtrip."""
    original = HeadToHeadResult(
        line_id="test",
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
    )
    json_data = original.model_dump()
    reconstructed = HeadToHeadResult.model_validate(json_data)
    assert reconstructed == original


def test_head_to_head_result_candidate_names() -> None:
    """Test HeadToHeadResult includes candidate names for N-way tracking."""
    result = HeadToHeadResult(
        line_id="line1",
        source_text="源",
        candidate_a_name="gpt4-full",
        candidate_b_name="claude-minimal",
        translation_a="Translation A",
        translation_b="Translation B",
        winner="A",
        reasoning="A preserves context better",
    )
    assert result.candidate_a_name == "gpt4-full"
    assert result.candidate_b_name == "claude-minimal"
