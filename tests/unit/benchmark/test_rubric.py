"""Unit tests for rubric and scoring schemas."""

import pytest
from pydantic import ValidationError

from rentl_schemas.benchmark.rubric import (
    HeadToHeadResult,
    LineScore,
    RubricDimension,
    RubricScore,
)


def test_rubric_dimension_enum() -> None:
    """Test RubricDimension enum values."""
    assert RubricDimension.ACCURACY == "accuracy"
    assert RubricDimension.STYLE_FIDELITY == "style_fidelity"
    assert RubricDimension.CONSISTENCY == "consistency"


def test_rubric_score_valid() -> None:
    """Test RubricScore with valid data."""
    score = RubricScore(
        dimension=RubricDimension.ACCURACY,
        score=4,
        reasoning="The translation accurately captures the source meaning.",
    )
    assert score.dimension == RubricDimension.ACCURACY
    assert score.score == 4
    assert "accurately" in score.reasoning


def test_rubric_score_out_of_range() -> None:
    """Test RubricScore validates score range (1-5)."""
    # Valid scores
    for value in [1, 2, 3, 4, 5]:
        score = RubricScore(
            dimension=RubricDimension.ACCURACY,
            score=value,
            reasoning="Test",
        )
        assert score.score == value

    # Invalid scores
    for value in [0, 6, -1, 10]:
        with pytest.raises(ValidationError):
            RubricScore(
                dimension=RubricDimension.ACCURACY,
                score=value,
                reasoning="Test",
            )


def test_rubric_score_roundtrip() -> None:
    """Test RubricScore serialization roundtrip."""
    original = RubricScore(
        dimension=RubricDimension.STYLE_FIDELITY,
        score=3,
        reasoning="Acceptable style but could be more natural.",
    )
    json_data = original.model_dump()
    reconstructed = RubricScore.model_validate(json_data)
    assert reconstructed == original


def test_line_score_valid() -> None:
    """Test LineScore with valid data."""
    line_score = LineScore(
        line_id="scene1_line5",
        source_text="こんにちは",
        translation="Hello",
        reference="Hi there",
        scores=[
            RubricScore(
                dimension=RubricDimension.ACCURACY,
                score=5,
                reasoning="Perfect translation",
            ),
            RubricScore(
                dimension=RubricDimension.STYLE_FIDELITY,
                score=4,
                reasoning="Natural but slightly informal",
            ),
        ],
    )
    assert line_score.line_id == "scene1_line5"
    assert line_score.source_text == "こんにちは"
    assert line_score.translation == "Hello"
    assert line_score.reference == "Hi there"
    assert len(line_score.scores) == 2


def test_line_score_no_reference() -> None:
    """Test LineScore without reference translation."""
    line_score = LineScore(
        line_id="test_line",
        source_text="テスト",
        translation="Test",
        scores=[
            RubricScore(
                dimension=RubricDimension.ACCURACY,
                score=5,
                reasoning="Correct",
            )
        ],
    )
    assert line_score.reference is None


def test_line_score_roundtrip() -> None:
    """Test LineScore serialization roundtrip."""
    original = LineScore(
        line_id="test",
        source_text="源文",
        translation="Source text",
        scores=[
            RubricScore(
                dimension=RubricDimension.CONSISTENCY,
                score=4,
                reasoning="Good consistency",
            )
        ],
    )
    json_data = original.model_dump()
    reconstructed = LineScore.model_validate(json_data)
    assert reconstructed == original


def test_head_to_head_result_valid() -> None:
    """Test HeadToHeadResult with valid data."""
    result = HeadToHeadResult(
        line_id="scene1_line10",
        source_text="ありがとう",
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
    assert result.winner == "A"
    assert len(result.dimension_winners) == 3


def test_head_to_head_result_tie() -> None:
    """Test HeadToHeadResult with tie winner."""
    result = HeadToHeadResult(
        line_id="test_line",
        source_text="テスト",
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
