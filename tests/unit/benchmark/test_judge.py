"""Unit tests for LLM judge rubric evaluation."""

import asyncio
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import AgentRunResult

from rentl_core.benchmark.judge import JudgeOutput, RubricJudge
from rentl_schemas.benchmark.rubric import RubricDimension
from rentl_schemas.io import TranslatedLine


@pytest.fixture
def mock_agent_result() -> AgentRunResult[JudgeOutput]:
    """Create mock pydantic-ai Agent result.

    Returns:
        AgentRunResult: Mocked result with JudgeOutput.
    """
    result = MagicMock(spec=AgentRunResult)
    result.output = JudgeOutput(
        overall_winner="A",
        reasoning="Translation A is more accurate",
        accuracy_winner="A",
        style_fidelity_winner="tie",
        consistency_winner="B",
    )
    return result


def test_head_to_head_prompt_construction() -> None:
    """Test head-to-head prompt labels translations A and B."""
    judge = RubricJudge(
        model_id="gpt-5-nano",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
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
    assert "ACCURACY" in prompt
    assert "STYLE FIDELITY" in prompt
    assert "CONSISTENCY" in prompt


@pytest.mark.asyncio
async def test_compare_head_to_head(
    mock_agent_result: AgentRunResult[JudgeOutput],
) -> None:
    """Test head-to-head comparison using pydantic-ai Agent."""
    with patch("rentl_core.benchmark.judge.Agent") as mock_agent_class:
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_agent_result)
        mock_agent_class.return_value = mock_agent_instance

        judge = RubricJudge(
            model_id="gpt-5-nano",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
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
        assert result.reasoning == "Translation A is more accurate"
        assert result.dimension_winners[RubricDimension.ACCURACY] == "A"
        assert result.dimension_winners[RubricDimension.STYLE_FIDELITY] == "tie"
        assert result.dimension_winners[RubricDimension.CONSISTENCY] == "B"
        assert (
            result.presented_as_a == "candidate_1"
        )  # No randomization, so candidate_1 was presented as A

        # Verify Agent was created with correct parameters
        mock_agent_class.assert_called_once()
        call_kwargs = mock_agent_class.call_args[1]
        assert call_kwargs["output_type"] == JudgeOutput
        assert call_kwargs["output_retries"] == 5


@pytest.mark.asyncio
async def test_compare_batch_head_to_head(
    mock_agent_result: AgentRunResult[JudgeOutput],
) -> None:
    """Test batch head-to-head comparison."""
    with patch("rentl_core.benchmark.judge.Agent") as mock_agent_class:
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_agent_result)
        mock_agent_class.return_value = mock_agent_instance

        judge = RubricJudge(
            model_id="gpt-5-nano",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
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
        # Agent is created once per comparison
        assert mock_agent_class.call_count == 2


@pytest.mark.asyncio
async def test_compare_batch_mismatched_line_ids() -> None:
    """Test batch comparison fails when line IDs don't match."""
    judge = RubricJudge(
        model_id="gpt-5-nano",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
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
async def test_compare_head_to_head_with_randomization() -> None:
    """Test head-to-head comparison correctly remaps winners when order is randomized.

    When randomize_order=True and the coin flip swaps A/B assignments, the judge
    sees translation_2 as "A" and translation_1 as "B". The returned result must
    remap winners back to the original translation_1/translation_2 labels.
    """
    # Mock result where judge picks "A" (which is translation_2 due to swap)
    mock_result = MagicMock(spec=AgentRunResult)
    mock_result.output = JudgeOutput(
        overall_winner="A",
        reasoning="A is more accurate",
        accuracy_winner="A",
        style_fidelity_winner="B",
        consistency_winner="tie",
    )

    with patch("rentl_core.benchmark.judge.Agent") as mock_agent_class:
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        judge = RubricJudge(
            model_id="gpt-5-nano",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )

        # Seed random to force swap (values <0.5 cause swap)
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
        # Judge returns: overall="A", accuracy="A", style_fidelity="B",
        # consistency="tie"
        # After remap: overall="B", accuracy="B", style_fidelity="A",
        # consistency="tie"
        assert result.translation_a == "Hello"
        assert result.translation_b == "Hi there"
        assert result.winner == "B"  # Judge said "A", but A was translation_2
        assert result.dimension_winners[RubricDimension.ACCURACY] == "B"
        assert result.dimension_winners[RubricDimension.STYLE_FIDELITY] == "A"
        assert result.dimension_winners[RubricDimension.CONSISTENCY] == "tie"
        assert (
            result.presented_as_a == "candidate_2"
        )  # After swap, candidate_2 was presented as A


@pytest.mark.asyncio
async def test_compare_head_to_head_with_tie() -> None:
    """Test head-to-head comparison with tie result."""
    mock_result = MagicMock(spec=AgentRunResult)
    mock_result.output = JudgeOutput(
        overall_winner="tie",
        reasoning="Both translations are equally good",
        accuracy_winner="tie",
        style_fidelity_winner="tie",
        consistency_winner="tie",
    )

    with patch("rentl_core.benchmark.judge.Agent") as mock_agent_class:
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent_instance

        judge = RubricJudge(
            model_id="gpt-5-nano",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )

        result = await judge.compare_head_to_head(
            line_id="line_1",
            source_text="こんにちは",
            translation_1="Hello",
            translation_2="Hi there",
            candidate_1_name="c1",
            candidate_2_name="c2",
            randomize_order=False,
        )

        assert result.winner == "tie"
        assert result.reasoning == "Both translations are equally good"
        assert result.dimension_winners[RubricDimension.ACCURACY] == "tie"
        assert result.dimension_winners[RubricDimension.STYLE_FIDELITY] == "tie"
        assert result.dimension_winners[RubricDimension.CONSISTENCY] == "tie"


@pytest.mark.asyncio
async def test_compare_head_to_head_with_progress_callback(
    mock_agent_result: AgentRunResult[JudgeOutput],
) -> None:
    """Test progress callback is invoked after comparison."""
    progress_calls: list[str] = []

    async def progress_cb(line_id: str) -> None:
        await asyncio.sleep(0)  # Make it truly async
        progress_calls.append(line_id)

    with patch("rentl_core.benchmark.judge.Agent") as mock_agent_class:
        mock_agent_instance = MagicMock()
        mock_agent_instance.run = AsyncMock(return_value=mock_agent_result)
        mock_agent_class.return_value = mock_agent_instance

        judge = RubricJudge(
            model_id="gpt-5-nano",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )

        await judge.compare_head_to_head(
            line_id="line_1",
            source_text="こんにちは",
            translation_1="Hello",
            translation_2="Hi there",
            candidate_1_name="c1",
            candidate_2_name="c2",
            randomize_order=False,
            progress_callback=progress_cb,
        )

        assert progress_calls == ["line_1"]


def test_judge_creates_openrouter_model_when_detected() -> None:
    """Test judge uses create_model factory with OpenRouter config."""
    mock_model = MagicMock()
    mock_settings = MagicMock()

    with patch(
        "rentl_core.benchmark.judge.create_model",
        return_value=(mock_model, mock_settings),
    ) as mock_factory:
        judge = RubricJudge(
            model_id="anthropic/claude-4.5-sonnet",
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            openrouter_require_parameters=True,
        )

        # Verify factory was called with correct parameters
        mock_factory.assert_called_once()
        call_kwargs = mock_factory.call_args.kwargs
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["model_id"] == "anthropic/claude-4.5-sonnet"
        assert call_kwargs["openrouter_provider"].require_parameters is True

        # Verify model and settings from factory are stored
        assert judge.model is mock_model
        assert judge.model_settings is mock_settings


def test_judge_creates_openai_model_when_not_openrouter() -> None:
    """Test judge uses create_model factory for non-OpenRouter endpoints."""
    mock_model = MagicMock()
    mock_settings = MagicMock()

    with patch(
        "rentl_core.benchmark.judge.create_model",
        return_value=(mock_model, mock_settings),
    ) as mock_factory:
        judge = RubricJudge(
            model_id="gpt-5-nano",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
        )

        # Verify factory was called with correct parameters
        mock_factory.assert_called_once()
        call_kwargs = mock_factory.call_args.kwargs
        assert call_kwargs["base_url"] == "https://api.openai.com/v1"
        assert call_kwargs["api_key"] == "test-key"
        assert call_kwargs["model_id"] == "gpt-5-nano"

        # Verify model and settings from factory are stored
        assert judge.model is mock_model
        assert judge.model_settings is mock_settings
