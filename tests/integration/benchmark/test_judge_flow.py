"""Integration tests for judge evaluation flow with mocked LLM."""

import asyncio
import json
import random
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic_ai import Agent, AgentRunResult
from pytest_bdd import given, parsers, scenario, then, when

from rentl_core.benchmark.judge import JudgeOutput, RubricJudge
from rentl_schemas.benchmark.rubric import RubricDimension
from rentl_schemas.io import TranslatedLine

FEATURES_DIR = Path(__file__).parent / "features"


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
    """Set up judge with mocked pydantic-ai Agent."""

    async def mock_agent_run(
        self: Agent[str, JudgeOutput], prompt: str, **kwargs: str | int | bool | None
    ) -> AgentRunResult[JudgeOutput]:
        """Mock pydantic-ai Agent.run that returns canned responses.

        Args:
            self: Agent instance (unused).
            prompt: User prompt (unused).
            **kwargs: Additional arguments (unused).

        Returns:
            AgentRunResult with mock JudgeOutput.

        Raises:
            RuntimeError: If no mock responses are available.
        """
        await asyncio.sleep(0)  # Make it truly async

        # Pop next mock response from queue
        if not ctx.mock_responses:
            raise RuntimeError("No mock responses available")

        response_text = ctx.mock_responses.pop(0)
        response_data = json.loads(response_text)

        # Create JudgeOutput from mocked JSON
        judge_output = JudgeOutput(
            overall_winner=response_data["overall_winner"],
            reasoning=response_data["reasoning"],
            accuracy_winner=response_data["accuracy_winner"],
            style_fidelity_winner=response_data["style_fidelity_winner"],
            consistency_winner=response_data["consistency_winner"],
        )

        # Create mock result
        result = MagicMock(spec=AgentRunResult)
        result.output = judge_output
        return result

    # Patch Agent.run across all instances
    monkeypatch.setattr("pydantic_ai.Agent.run", mock_agent_run)

    ctx.judge = RubricJudge(
        model_id="gpt-5-nano",
        base_url="https://api.openai.com/v1",
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
            "accuracy_winner": "tie",
            "style_fidelity_winner": "B",
            "consistency_winner": "B",
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
            "accuracy_winner": "A",
            "style_fidelity_winner": "B",
            "consistency_winner": "B",
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
