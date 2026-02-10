"""Integration tests for judge evaluation flow with mocked LLM."""

import asyncio
import json
import random
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from rentl_core.benchmark.judge import RubricJudge
from rentl_llm.openai_runtime import OpenAICompatibleRuntime
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

FEATURES_DIR = Path(__file__).parent.parent.parent / "features" / "benchmark"


@scenario(
    str(FEATURES_DIR / "judge_evaluation.feature"),
    "Head-to-head comparison",
)
def test_head_to_head_comparison() -> None:
    """Test head-to-head comparison flow."""


@scenario(
    str(FEATURES_DIR / "judge_evaluation.feature"),
    "Head-to-head comparison with randomized order",
)
def test_head_to_head_with_randomization() -> None:
    """Test head-to-head comparison with randomized A/B assignment."""


class JudgeContext:
    """Shared context for judge integration tests."""

    def __init__(self) -> None:
        """Initialize judge test context."""
        self.judge: RubricJudge | None = None
        self.translations_mtl: list[TranslatedLine] = []
        self.translations_rentl: list[TranslatedLine] = []
        self.head_to_head_results: list = []
        self.mock_responses: list[str] = []


@pytest.fixture
def ctx() -> JudgeContext:
    """Provide test context.

    Returns:
        JudgeContext: Test context instance.
    """
    return JudgeContext()


@given("a rubric judge with mocked LLM")
def given_judge_with_mock(ctx: JudgeContext, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up judge with mocked LLM runtime."""

    def mock_run_prompt_sync(
        self: object, request: object, *, api_key: str
    ) -> LlmPromptResponse:
        """Mock LLM runtime that returns canned responses.

        Args:
            self: OpenAIRuntime instance (unused).
            request: LlmPromptRequest instance (unused).
            api_key: API key (unused).

        Returns:
            LlmPromptResponse with mock response text.

        Raises:
            RuntimeError: If no mock responses are available.
        """
        # Pop next mock response from queue
        if not ctx.mock_responses:
            raise RuntimeError("No mock responses available")

        response_text = ctx.mock_responses.pop(0)
        return LlmPromptResponse(model_id="gpt-4o-mini", output_text=response_text)

    # Wrap sync mock in async function
    async def mock_run_prompt_async(
        self: object, request: object, *, api_key: str
    ) -> LlmPromptResponse:
        """Async wrapper for mock LLM runtime.

        Returns:
            LlmPromptResponse: Mock LLM response.
        """
        # Use asyncio to ensure proper async execution
        await asyncio.sleep(0)
        return mock_run_prompt_sync(self, request, api_key=api_key)

    monkeypatch.setattr(OpenAICompatibleRuntime, "run_prompt", mock_run_prompt_async)

    runtime_settings = LlmRuntimeSettings(
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

    ctx.judge = RubricJudge(
        runtime=OpenAICompatibleRuntime(),
        runtime_settings=runtime_settings,
        api_key="test-key",
    )


@given("MTL translations")
def given_mtl_translations(ctx: JudgeContext, datatable: list) -> None:
    """Set up MTL baseline translations."""
    lines = []
    # datatable is a list of lists: first row is header, rest are data
    for row in datatable[1:]:  # Skip header row
        line_id, source, translation = row

        lines.append(
            TranslatedLine(
                line_id=line_id,
                text=translation,
                source_text=source,
            )
        )

    ctx.translations_mtl = lines


@given("rentl translations")
def given_rentl_translations(ctx: JudgeContext, datatable: list) -> None:
    """Set up rentl pipeline translations."""
    lines = []
    # datatable is a list of lists: first row is header, rest are data
    for row in datatable[1:]:  # Skip header row
        line_id, source, translation = row

        lines.append(
            TranslatedLine(
                line_id=line_id,
                text=translation,
                source_text=source,
            )
        )

    ctx.translations_rentl = lines


@given("judge responds with comparison")
def given_judge_comparison(ctx: JudgeContext, docstring: str) -> None:
    """Configure mock head-to-head responses for winner B."""
    # docstring contains the triple-quoted text from the feature file
    for _ in ctx.translations_mtl:
        mock_response = json.dumps({
            "overall_winner": "B",
            "reasoning": "Translation B is more natural",
            "dimension_winners": {
                "accuracy": "tie",
                "style_fidelity": "B",
                "consistency": "B",
            },
        })
        ctx.mock_responses.append(mock_response)


@given("judge responds with winner A")
def given_judge_winner_a(ctx: JudgeContext, docstring: str) -> None:
    """Configure mock head-to-head responses for winner A."""
    # docstring contains the triple-quoted text from the feature file
    for _ in ctx.translations_mtl:
        mock_response = json.dumps({
            "overall_winner": "A",
            "reasoning": "Translation A is more accurate",
            "dimension_winners": {
                "accuracy": "A",
                "style_fidelity": "B",
                "consistency": "B",
            },
        })
        ctx.mock_responses.append(mock_response)


@when("I compare translations head-to-head")
def when_compare_head_to_head(ctx: JudgeContext) -> None:
    """Execute head-to-head comparison."""
    assert ctx.judge is not None
    ctx.head_to_head_results = asyncio.run(
        ctx.judge.compare_batch_head_to_head(
            ctx.translations_mtl,
            ctx.translations_rentl,
            candidate_1_name="mtl",
            candidate_2_name="rentl",
            randomize_order=False,
        )
    )


@when("I compare translations head-to-head with randomization")
def when_compare_head_to_head_randomized(ctx: JudgeContext) -> None:
    """Execute head-to-head comparison with randomized order."""
    assert ctx.judge is not None
    # Seed random to force swap behavior (seed(1) produces <0.5 on first call)
    random.seed(1)
    ctx.head_to_head_results = asyncio.run(
        ctx.judge.compare_batch_head_to_head(
            ctx.translations_mtl,
            ctx.translations_rentl,
            candidate_1_name="mtl",
            candidate_2_name="rentl",
            randomize_order=True,
        )
    )


@then(parsers.parse("each comparison has a winner (A, B, or tie)"))
def then_comparison_has_winner(ctx: JudgeContext) -> None:
    """Verify each comparison has a winner."""
    assert len(ctx.head_to_head_results) > 0
    for result in ctx.head_to_head_results:
        assert result.winner in ("A", "B", "tie")


@then("each comparison includes reasoning")
def then_comparison_includes_reasoning(ctx: JudgeContext) -> None:
    """Verify comparisons include reasoning."""
    for result in ctx.head_to_head_results:
        assert result.reasoning is not None
        assert len(result.reasoning) > 0


@then("each comparison includes both translations")
def then_comparison_includes_both(ctx: JudgeContext) -> None:
    """Verify comparisons include both translations."""
    for result in ctx.head_to_head_results:
        assert result.translation_a is not None
        assert result.translation_b is not None
        assert len(result.translation_a) > 0
        assert len(result.translation_b) > 0


@then("dimension winners are tracked per comparison")
def then_dimension_winners_tracked(ctx: JudgeContext) -> None:
    """Verify per-dimension winners are tracked."""
    for result in ctx.head_to_head_results:
        # All three dimensions must have winners
        assert len(result.dimension_winners) == 3
        # Verify all required dimensions are present
        assert RubricDimension.ACCURACY in result.dimension_winners
        assert RubricDimension.STYLE_FIDELITY in result.dimension_winners
        assert RubricDimension.CONSISTENCY in result.dimension_winners
        # Verify all winners are valid
        for dim, winner in result.dimension_winners.items():
            assert isinstance(dim, RubricDimension)
            assert winner in ("A", "B", "tie")


@then("randomization remaps winners correctly")
def then_randomization_remaps_correctly(ctx: JudgeContext) -> None:
    """Verify randomization correctly remaps winners.

    With seed(1), the random swap occurs, so:
    - Judge sees: A=rentl (translation_2), B=MTL (translation_1)
    - Judge returns: winner="A"
    - After remap: winner="B" (because A in judge-space is translation_2, which is "B")
    """
    assert len(ctx.head_to_head_results) == 1
    result = ctx.head_to_head_results[0]

    # The mock judge response says winner="A" (see given_judge_comparison)
    # With swap: judge's "A" is translation_2 (rentl), which maps to result's "B"
    # So final winner should be "B"
    assert result.winner == "B"

    # Verify dimension winners are also remapped
    # Mock says: accuracy="A", style_fidelity="B", consistency="B"
    # After remap: accuracy="B", style_fidelity="A", consistency="A"
    assert result.dimension_winners[RubricDimension.ACCURACY] == "B"
    assert result.dimension_winners[RubricDimension.STYLE_FIDELITY] == "A"
    assert result.dimension_winners[RubricDimension.CONSISTENCY] == "A"
