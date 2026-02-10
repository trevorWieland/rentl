"""Unit tests for LLM judge rubric evaluation."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rentl_core.benchmark.judge import RubricJudge
from rentl_schemas.benchmark.rubric import RubricDimension
from rentl_schemas.config import RetryConfig
from rentl_schemas.io import TranslatedLine
from rentl_schemas.llm import (
    LlmEndpointTarget,
    LlmModelSettings,
    LlmPromptResponse,
    LlmRuntimeSettings,
)
from rentl_schemas.primitives import ReasoningEffort


@pytest.fixture
def runtime_settings() -> LlmRuntimeSettings:
    """Create test runtime settings.

    Returns:
        LlmRuntimeSettings: Test runtime configuration.
    """
    return LlmRuntimeSettings(
        endpoint=LlmEndpointTarget(
            provider_name="openai",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            timeout_s=30.0,
        ),
        model=LlmModelSettings(
            model_id="gpt-4o-mini",
            temperature=0.7,
            max_output_tokens=1000,
            reasoning_effort=ReasoningEffort.MEDIUM,
            top_p=1.0,
            presence_penalty=0.0,
            frequency_penalty=0.0,
        ),
        retry=RetryConfig(
            max_retries=3,
            backoff_s=1.0,
            max_backoff_s=10.0,
        ),
    )


@pytest.fixture
def mock_runtime() -> MagicMock:
    """Create mock LLM runtime.

    Returns:
        MagicMock: Mocked runtime instance.
    """
    return MagicMock()


def test_reference_based_prompt_construction(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test reference-based prompt includes source, reference, and candidate."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    prompt = judge._build_reference_based_prompt(
        source_text="こんにちは",
        reference="Hello",
        candidate="Hi there",
    )

    assert "こんにちは" in prompt
    assert "Hello" in prompt
    assert "Hi there" in prompt
    assert "ACCURACY" in prompt
    assert "STYLE FIDELITY" in prompt
    assert "CONSISTENCY" in prompt
    assert "1-5" in prompt


def test_reference_free_prompt_construction(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test reference-free prompt excludes reference translation."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    prompt = judge._build_reference_free_prompt(
        source_text="こんにちは",
        candidate="Hi there",
    )

    assert "こんにちは" in prompt
    assert "Hi there" in prompt
    assert "Reference translation" not in prompt
    assert "known-good" not in prompt
    assert "ACCURACY" in prompt
    assert "STYLE FIDELITY" in prompt
    assert "CONSISTENCY" in prompt


def test_head_to_head_prompt_construction(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test head-to-head prompt labels translations A and B."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    prompt = judge._build_head_to_head_prompt(
        source_text="こんにちは",
        translation_a="Hello",
        translation_b="Hi there",
    )

    assert "こんにちは" in prompt
    assert "Translation A" in prompt
    assert "Translation B" in prompt
    assert "Hello" in prompt
    assert "Hi there" in prompt
    assert "overall_winner" in prompt
    assert "dimension_winners" in prompt


def test_parse_rubric_scores_from_json(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing judge response with rubric scores."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "accuracy": {"score": 5, "reasoning": "Perfect translation"},
        "style_fidelity": {"score": 4, "reasoning": "Natural but minor issues"},
        "consistency": {"score": 5, "reasoning": "Consistent terminology"},
    })

    scores = judge._parse_rubric_scores(response)

    assert len(scores) == 3
    assert scores[0].dimension == RubricDimension.ACCURACY
    assert scores[0].score == 5
    assert scores[0].reasoning == "Perfect translation"
    assert scores[1].dimension == RubricDimension.STYLE_FIDELITY
    assert scores[1].score == 4
    assert scores[2].dimension == RubricDimension.CONSISTENCY
    assert scores[2].score == 5


def test_parse_rubric_scores_from_markdown_json(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing rubric scores from markdown-wrapped JSON."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = """```json
{
    "accuracy": {"score": 3, "reasoning": "Some issues"},
    "style_fidelity": {"score": 3, "reasoning": "Awkward phrasing"},
    "consistency": {"score": 4, "reasoning": "Mostly consistent"}
}
```"""

    scores = judge._parse_rubric_scores(response)

    assert len(scores) == 3
    assert scores[0].score == 3
    assert scores[1].score == 3
    assert scores[2].score == 4


def test_parse_rubric_scores_missing_dimension(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing fails when dimension is missing."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "accuracy": {"score": 5, "reasoning": "Good"},
        # Missing style_fidelity and consistency
    })

    with pytest.raises(ValueError, match="Missing dimension"):
        judge._parse_rubric_scores(response)


def test_parse_head_to_head_from_json(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing head-to-head comparison result."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "overall_winner": "A",
        "reasoning": "Translation A is more accurate",
        "dimension_winners": {
            "accuracy": "A",
            "style_fidelity": "tie",
            "consistency": "B",
        },
    })

    winner, reasoning, dim_winners = judge._parse_head_to_head(response)

    assert winner == "A"
    assert reasoning == "Translation A is more accurate"
    assert dim_winners[RubricDimension.ACCURACY] == "A"
    assert dim_winners[RubricDimension.STYLE_FIDELITY] == "tie"
    assert dim_winners[RubricDimension.CONSISTENCY] == "B"


def test_parse_head_to_head_with_tie(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing head-to-head with tie result."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "overall_winner": "tie",
        "reasoning": "Both translations are equally good",
        "dimension_winners": {
            "accuracy": "tie",
            "style_fidelity": "tie",
            "consistency": "tie",
        },
    })

    winner, reasoning, _dim_winners = judge._parse_head_to_head(response)

    assert winner == "tie"
    assert reasoning == "Both translations are equally good"


def test_parse_head_to_head_invalid_winner(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing fails with invalid winner value."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "overall_winner": "C",  # Invalid
        "reasoning": "Something",
    })

    with pytest.raises(ValueError, match="Invalid overall_winner"):
        judge._parse_head_to_head(response)


@pytest.mark.asyncio
async def test_score_translation_reference_based(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test scoring a single translation with reference."""
    mock_runtime.run_prompt = AsyncMock(
        return_value=LlmPromptResponse(
            model_id="gpt-4o-mini",
            output_text=json.dumps({
                "accuracy": {"score": 5, "reasoning": "Accurate"},
                "style_fidelity": {"score": 4, "reasoning": "Natural"},
                "consistency": {"score": 5, "reasoning": "Consistent"},
            }),
        )
    )

    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    result = await judge.score_translation(
        line_id="line_1",
        source_text="こんにちは",
        translation="Hello",
        reference="Hello",
    )

    assert result.line_id == "line_1"
    assert result.source_text == "こんにちは"
    assert result.translation == "Hello"
    assert result.reference == "Hello"
    assert len(result.scores) == 3
    assert result.scores[0].dimension == RubricDimension.ACCURACY
    assert result.scores[0].score == 5


@pytest.mark.asyncio
async def test_score_translation_reference_free(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test scoring a single translation without reference."""
    mock_runtime.run_prompt = AsyncMock(
        return_value=LlmPromptResponse(
            model_id="gpt-4o-mini",
            output_text=json.dumps({
                "accuracy": {"score": 4, "reasoning": "Good"},
                "style_fidelity": {"score": 3, "reasoning": "Awkward"},
                "consistency": {"score": 4, "reasoning": "Consistent"},
            }),
        )
    )

    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    result = await judge.score_translation(
        line_id="line_1",
        source_text="こんにちは",
        translation="Hi there",
        reference=None,
    )

    assert result.line_id == "line_1"
    assert result.reference is None
    assert len(result.scores) == 3


@pytest.mark.asyncio
async def test_score_batch(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test scoring multiple translations in parallel."""
    mock_runtime.run_prompt = AsyncMock(
        return_value=LlmPromptResponse(
            model_id="gpt-4o-mini",
            output_text=json.dumps({
                "accuracy": {"score": 5, "reasoning": "Good"},
                "style_fidelity": {"score": 4, "reasoning": "Natural"},
                "consistency": {"score": 5, "reasoning": "Consistent"},
            }),
        )
    )

    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    translations = [
        TranslatedLine(
            line_id="line_1",
            text="Hello",
            source_text="こんにちは",
        ),
        TranslatedLine(
            line_id="line_2",
            text="Goodbye",
            source_text="さようなら",
        ),
    ]

    results = await judge.score_batch(translations)

    assert len(results) == 2
    assert results[0].line_id == "line_1"
    assert results[1].line_id == "line_2"
    assert mock_runtime.run_prompt.call_count == 2


@pytest.mark.asyncio
async def test_compare_head_to_head(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test head-to-head comparison between two translations."""
    mock_runtime.run_prompt = AsyncMock(
        return_value=LlmPromptResponse(
            model_id="gpt-4o-mini",
            output_text=json.dumps({
                "overall_winner": "A",
                "reasoning": "A is more accurate",
                "dimension_winners": {
                    "accuracy": "A",
                    "style_fidelity": "tie",
                    "consistency": "A",
                },
            }),
        )
    )

    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    result = await judge.compare_head_to_head(
        line_id="line_1",
        source_text="こんにちは",
        translation_1="Hello",
        translation_2="Hi there",
        randomize_order=False,
    )

    assert result.line_id == "line_1"
    assert result.translation_a == "Hello"
    assert result.translation_b == "Hi there"
    assert result.winner == "A"
    assert result.reasoning == "A is more accurate"


@pytest.mark.asyncio
async def test_compare_batch_head_to_head(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test batch head-to-head comparison."""
    mock_runtime.run_prompt = AsyncMock(
        return_value=LlmPromptResponse(
            model_id="gpt-4o-mini",
            output_text=json.dumps({
                "overall_winner": "B",
                "reasoning": "B is better",
                "dimension_winners": {
                    "accuracy": "B",
                    "style_fidelity": "B",
                    "consistency": "tie",
                },
            }),
        )
    )

    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    trans1 = [
        TranslatedLine(line_id="line_1", text="Hello", source_text="こんにちは"),
        TranslatedLine(line_id="line_2", text="Goodbye", source_text="さようなら"),
    ]

    trans2 = [
        TranslatedLine(line_id="line_1", text="Hi", source_text="こんにちは"),
        TranslatedLine(line_id="line_2", text="Bye", source_text="さようなら"),
    ]

    results = await judge.compare_batch_head_to_head(
        trans1, trans2, randomize_order=False
    )

    assert len(results) == 2
    assert results[0].line_id == "line_1"
    assert results[1].line_id == "line_2"
    assert mock_runtime.run_prompt.call_count == 2


@pytest.mark.asyncio
async def test_compare_batch_mismatched_line_ids(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test batch comparison fails when line IDs don't match."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    trans1 = [
        TranslatedLine(line_id="line_1", text="Hello", source_text="こんにちは"),
    ]

    trans2 = [
        TranslatedLine(line_id="line_2", text="Hi", source_text="こんにちは"),
    ]

    with pytest.raises(ValueError, match="not found in second translation set"):
        await judge.compare_batch_head_to_head(trans1, trans2)
