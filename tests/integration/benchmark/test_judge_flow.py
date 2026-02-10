"""Integration tests for judge evaluation flow with mocked LLM."""

import asyncio
import json
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
    "Reference-based rubric evaluation",
)
def test_reference_based_evaluation() -> None:
    """Test reference-based rubric evaluation flow."""


@scenario(
    str(FEATURES_DIR / "judge_evaluation.feature"),
    "Reference-free rubric evaluation",
)
def test_reference_free_evaluation() -> None:
    """Test reference-free rubric evaluation flow."""


@scenario(
    str(FEATURES_DIR / "judge_evaluation.feature"),
    "Head-to-head comparison",
)
def test_head_to_head_comparison() -> None:
    """Test head-to-head comparison flow."""


class JudgeContext:
    """Shared context for judge integration tests."""

    def __init__(self) -> None:
        """Initialize judge test context."""
        self.judge: RubricJudge | None = None
        self.translations: list[TranslatedLine] = []
        self.references: dict[str, str] = {}
        self.translations_mtl: list[TranslatedLine] = []
        self.translations_rentl: list[TranslatedLine] = []
        self.rubric_results: list = []
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


@given(parsers.parse("translation lines:\n{lines_table}"))
def given_translation_lines(ctx: JudgeContext, lines_table: str) -> None:
    """Set up translation lines for evaluation."""
    lines = []
    for row in lines_table.strip().split("\n")[1:]:  # Skip header
        parts = [p.strip() for p in row.split("|")[1:-1]]  # Remove outer pipes
        line_id, source, translation = parts

        lines.append(
            TranslatedLine(
                line_id=line_id,
                text=translation,
                source_text=source,
            )
        )

    ctx.translations = lines


@given(parsers.parse("reference translations:\n{refs_table}"))
def given_reference_translations(ctx: JudgeContext, refs_table: str) -> None:
    """Set up reference translations."""
    refs = {}
    for row in refs_table.strip().split("\n")[1:]:  # Skip header
        parts = [p.strip() for p in row.split("|")[1:-1]]
        line_id, reference = parts
        refs[line_id] = reference

    ctx.references = refs


@given(parsers.parse("MTL translations:\n{mtl_table}"))
def given_mtl_translations(ctx: JudgeContext, mtl_table: str) -> None:
    """Set up MTL baseline translations."""
    lines = []
    for row in mtl_table.strip().split("\n")[1:]:  # Skip header
        parts = [p.strip() for p in row.split("|")[1:-1]]
        line_id, source, translation = parts

        lines.append(
            TranslatedLine(
                line_id=line_id,
                text=translation,
                source_text=source,
            )
        )

    ctx.translations_mtl = lines


@given(parsers.parse("rentl translations:\n{rentl_table}"))
def given_rentl_translations(ctx: JudgeContext, rentl_table: str) -> None:
    """Set up rentl pipeline translations."""
    lines = []
    for row in rentl_table.strip().split("\n")[1:]:  # Skip header
        parts = [p.strip() for p in row.split("|")[1:-1]]
        line_id, source, translation = parts

        lines.append(
            TranslatedLine(
                line_id=line_id,
                text=translation,
                source_text=source,
            )
        )

    ctx.translations_rentl = lines


@given(parsers.parse("judge responds with scores:\n{scores}"))
def given_judge_scores(ctx: JudgeContext, scores: str) -> None:
    """Configure mock judge responses."""
    # Parse the expected score structure and create mock responses
    for _ in ctx.translations:
        mock_response = json.dumps({
            "accuracy": {"score": 5, "reasoning": "Accurate translation"},
            "style_fidelity": {"score": 4, "reasoning": "Natural style"},
            "consistency": {"score": 5, "reasoning": "Consistent terminology"},
        })
        ctx.mock_responses.append(mock_response)


@given(parsers.parse("judge responds with comparison:\n{comparison}"))
def given_judge_comparison(ctx: JudgeContext, comparison: str) -> None:
    """Configure mock head-to-head responses."""
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


@when("I score translations with reference-based mode")
def when_score_reference_based(ctx: JudgeContext) -> None:
    """Execute reference-based scoring."""
    assert ctx.judge is not None
    ctx.rubric_results = asyncio.run(
        ctx.judge.score_batch(ctx.translations, ctx.references)
    )


@when("I score translations with reference-free mode")
def when_score_reference_free(ctx: JudgeContext) -> None:
    """Execute reference-free scoring."""
    assert ctx.judge is not None
    ctx.rubric_results = asyncio.run(
        ctx.judge.score_batch(ctx.translations, references=None)
    )


@when("I compare translations head-to-head")
def when_compare_head_to_head(ctx: JudgeContext) -> None:
    """Execute head-to-head comparison."""
    assert ctx.judge is not None
    ctx.head_to_head_results = asyncio.run(
        ctx.judge.compare_batch_head_to_head(
            ctx.translations_mtl, ctx.translations_rentl, randomize_order=False
        )
    )


@then(parsers.parse("each line has scores for {count:d} dimensions"))
def then_line_has_dimension_scores(ctx: JudgeContext, count: int) -> None:
    """Verify each line has scores for all dimensions."""
    assert len(ctx.rubric_results) > 0
    for result in ctx.rubric_results:
        assert len(result.scores) == count


@then("each dimension score includes reasoning")
def then_scores_include_reasoning(ctx: JudgeContext) -> None:
    """Verify scores include reasoning text."""
    for result in ctx.rubric_results:
        for score in result.scores:
            assert score.reasoning is not None
            assert len(score.reasoning) > 0


@then("scores are in valid 1-5 range")
def then_scores_in_valid_range(ctx: JudgeContext) -> None:
    """Verify all scores are within valid range."""
    for result in ctx.rubric_results:
        for score in result.scores:
            assert 1 <= score.score <= 5


@then("each result includes source text and translation")
def then_results_include_text(ctx: JudgeContext) -> None:
    """Verify results include source and translation text."""
    for result in ctx.rubric_results:
        assert result.source_text is not None
        assert len(result.source_text) > 0
        assert result.translation is not None
        assert len(result.translation) > 0


@then("each result includes reference translation")
def then_results_include_reference(ctx: JudgeContext) -> None:
    """Verify results include reference translation."""
    for result in ctx.rubric_results:
        assert result.reference is not None
        assert len(result.reference) > 0


@then("each result does not include reference")
def then_results_exclude_reference(ctx: JudgeContext) -> None:
    """Verify results exclude reference translation."""
    for result in ctx.rubric_results:
        assert result.reference is None


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
        # Check at least one dimension has a winner
        assert len(result.dimension_winners) > 0
        for dim, winner in result.dimension_winners.items():
            assert isinstance(dim, RubricDimension)
            assert winner in ("A", "B", "tie")
