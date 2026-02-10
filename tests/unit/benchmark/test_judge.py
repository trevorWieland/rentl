"""Unit tests for LLM judge rubric evaluation."""

import json
import random
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
        candidate_1_name="candidate_1",
        candidate_2_name="candidate_2",
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
        trans1,
        trans2,
        candidate_1_name="candidate_1",
        candidate_2_name="candidate_2",
        randomize_order=False,
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
        await judge.compare_batch_head_to_head(
            trans1, trans2, candidate_1_name="c1", candidate_2_name="c2"
        )


@pytest.mark.asyncio
async def test_compare_head_to_head_with_randomization(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test head-to-head comparison correctly remaps winners when order is randomized.

    When randomize_order=True and the coin flip swaps A/B assignments, the judge
    sees translation_2 as "A" and translation_1 as "B". The returned result must
    remap winners back to the original translation_1/translation_2 labels.
    """
    # Mock response where judge picks "A" (which is translation_2 due to swap)
    mock_runtime.run_prompt = AsyncMock(
        return_value=LlmPromptResponse(
            model_id="gpt-4o-mini",
            output_text=json.dumps({
                "overall_winner": "A",
                "reasoning": "A is more accurate",
                "dimension_winners": {
                    "accuracy": "A",
                    "style_fidelity": "B",
                    "consistency": "tie",
                },
            }),
        )
    )

    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    # Seed random to force swap (values <0.5 cause swap at line 401)
    random.seed(1)  # seed(1) produces first value ~0.134, which DOES swap

    result = await judge.compare_head_to_head(
        line_id="line_1",
        source_text="こんにちは",
        translation_1="Hello",
        translation_2="Hi there",
        candidate_1_name="candidate_1",
        candidate_2_name="candidate_2",
        randomize_order=True,
    )

    # With seed(1), random.random() < 0.5, so swap occurs:
    # Judge sees: A="Hi there" (translation_2), B="Hello" (translation_1)
    # Judge returns: overall="A", accuracy="A", style_fidelity="B", consistency="tie"
    # After remap: overall="B", accuracy="B", style_fidelity="A", consistency="tie"
    # Because original assignment was: translation_1="Hello", translation_2="Hi there"
    # And A in judge-space maps to translation_2, B in judge-space maps to translation_1
    # So when judge picks A, that's translation_2, which is "B" in result-space
    assert result.translation_a == "Hello"
    assert result.translation_b == "Hi there"
    assert result.winner == "B"  # Judge said "A", but A was translation_2
    assert result.dimension_winners[RubricDimension.ACCURACY] == "B"
    assert result.dimension_winners[RubricDimension.STYLE_FIDELITY] == "A"
    assert result.dimension_winners[RubricDimension.CONSISTENCY] == "tie"


def test_parse_head_to_head_missing_dimension_winners(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing fails when dimension_winners is missing entirely."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "overall_winner": "A",
        "reasoning": "A is better",
        # Missing dimension_winners
    })

    with pytest.raises(ValueError, match="Missing 'dimension_winners'"):
        judge._parse_head_to_head(response)


def test_parse_head_to_head_missing_dimension(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing fails when a required dimension winner is missing."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "overall_winner": "A",
        "reasoning": "A is better",
        "dimension_winners": {
            "accuracy": "A",
            "style_fidelity": "B",
            # Missing consistency
        },
    })

    with pytest.raises(ValueError, match="Missing dimension winner for consistency"):
        judge._parse_head_to_head(response)


def test_parse_head_to_head_invalid_dimension_winner(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing fails when dimension winner has invalid value."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "overall_winner": "A",
        "reasoning": "A is better",
        "dimension_winners": {
            "accuracy": "C",  # Invalid
            "style_fidelity": "B",
            "consistency": "tie",
        },
    })

    with pytest.raises(ValueError, match="Invalid winner for accuracy"):
        judge._parse_head_to_head(response)


def test_parse_head_to_head_with_markdown_json_block(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing handles JSON wrapped in markdown code blocks."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = """```json
{
    "overall_winner": "A",
    "reasoning": "A is better",
    "dimension_winners": {
        "accuracy": "A",
        "style_fidelity": "B",
        "consistency": "tie"
    }
}
```"""

    winner, reasoning, dim_winners = judge._parse_head_to_head(response)

    assert winner == "A"
    assert reasoning == "A is better"
    assert dim_winners[RubricDimension.ACCURACY] == "A"


def test_parse_head_to_head_with_plain_markdown_block(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing handles JSON wrapped in plain markdown code blocks."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = """```
{
    "overall_winner": "B",
    "reasoning": "B is better",
    "dimension_winners": {
        "accuracy": "B",
        "style_fidelity": "B",
        "consistency": "A"
    }
}
```"""

    winner, reasoning, _dim_winners = judge._parse_head_to_head(response)

    assert winner == "B"
    assert reasoning == "B is better"


def test_parse_head_to_head_invalid_json(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing fails with invalid JSON."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = "This is not valid JSON at all"

    with pytest.raises(ValueError, match="Failed to parse judge response as JSON"):
        judge._parse_head_to_head(response)


def test_parse_head_to_head_missing_overall_winner(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test parsing fails when overall_winner is missing."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = json.dumps({
        "reasoning": "A is better",
        "dimension_winners": {
            "accuracy": "A",
            "style_fidelity": "B",
            "consistency": "tie",
        },
    })

    with pytest.raises(ValueError, match="Missing 'overall_winner' or 'reasoning'"):
        judge._parse_head_to_head(response)


def test_extract_json_from_text_with_reasoning_prefix(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test JSON extraction handles reasoning text before JSON object."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = """Let me think about this comparison carefully...

After analyzing both translations, here's my evaluation:

{
    "overall_winner": "A",
    "reasoning": "A is more accurate",
    "dimension_winners": {
        "accuracy": "A",
        "style_fidelity": "B",
        "consistency": "tie"
    }
}

This is my final verdict."""

    json_text = judge._extract_json_from_text(response)
    data = json.loads(json_text)

    assert data["overall_winner"] == "A"
    assert data["reasoning"] == "A is more accurate"


def test_extract_json_from_text_with_nested_objects(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test JSON extraction handles nested objects correctly."""
    judge = RubricJudge(
        runtime=mock_runtime, runtime_settings=runtime_settings, api_key="test-key"
    )

    response = """Here is my analysis:

{
    "overall_winner": "B",
    "reasoning": "B has better style",
    "dimension_winners": {
        "accuracy": "A",
        "style_fidelity": "B",
        "consistency": "tie"
    }
}"""

    json_text = judge._extract_json_from_text(response)
    data = json.loads(json_text)

    assert data["overall_winner"] == "B"
    assert "dimension_winners" in data


@pytest.mark.asyncio
async def test_compare_head_to_head_retry_on_parse_failure(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test retry logic on parse failure with eventual success."""
    # First call returns invalid JSON, second call succeeds
    mock_runtime.run_prompt = AsyncMock(
        side_effect=[
            LlmPromptResponse(
                model_id="gpt-4o-mini",
                output_text="Invalid response",
            ),
            LlmPromptResponse(
                model_id="gpt-4o-mini",
                output_text=json.dumps({
                    "overall_winner": "A",
                    "reasoning": "A is better",
                    "dimension_winners": {
                        "accuracy": "A",
                        "style_fidelity": "A",
                        "consistency": "tie",
                    },
                }),
            ),
        ]
    )

    judge = RubricJudge(
        runtime=mock_runtime,
        runtime_settings=runtime_settings,
        api_key="test-key",
        max_retries=3,
    )

    result = await judge.compare_head_to_head(
        line_id="line_1",
        source_text="こんにちは",
        translation_1="Hello",
        translation_2="Hi",
        candidate_1_name="c1",
        candidate_2_name="c2",
        randomize_order=False,
    )

    assert result.winner == "A"
    assert mock_runtime.run_prompt.call_count == 2  # Retried once


@pytest.mark.asyncio
async def test_compare_head_to_head_retry_exhaustion(
    mock_runtime: MagicMock, runtime_settings: LlmRuntimeSettings
) -> None:
    """Test retry logic fails after max retries exhausted."""
    # All calls return invalid JSON
    mock_runtime.run_prompt = AsyncMock(
        return_value=LlmPromptResponse(
            model_id="gpt-4o-mini",
            output_text="Invalid response every time",
        )
    )

    judge = RubricJudge(
        runtime=mock_runtime,
        runtime_settings=runtime_settings,
        api_key="test-key",
        max_retries=2,
    )

    with pytest.raises(ValueError, match="after 2 attempts"):
        await judge.compare_head_to_head(
            line_id="line_1",
            source_text="こんにちは",
            translation_1="Hello",
            translation_2="Hi",
            candidate_1_name="c1",
            candidate_2_name="c2",
            randomize_order=False,
        )

    assert mock_runtime.run_prompt.call_count == 2
