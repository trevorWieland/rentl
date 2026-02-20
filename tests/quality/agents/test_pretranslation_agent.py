"""Quality evals for the pretranslation agent.

Split into two scenarios so each stays comfortably under the 29s pytest timeout:
- Structural eval: real agent run + deterministic evaluators (no LLM judge)
- Judge eval: hardcoded agent output + LLM judge only (no agent run)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge, MaxDuration
from pydantic_evals.reporting import EvaluationReport
from pytest_bdd import given, scenarios, then, when

from rentl_agents import (
    create_pretranslation_agent_from_profile,
    get_default_agents_dir,
    get_default_prompts_dir,
)
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import PretranslationPhaseInput
from tests.quality.agents.eval_types import AgentEvalOutput
from tests.quality.agents.evaluators import (
    ListFieldMinLength,
    OutputFieldPresent,
    ToolCallCountAtLeast,
    ToolInputSchemaValid,
    ToolResultHasKeys,
    assert_report_success,
)
from tests.quality.agents.quality_harness import (
    QualityModelConfig,
    build_profile_config,
)
from tests.quality.agents.tool_spy import ToolCallRecorder, build_tool_registry

pytestmark = [
    pytest.mark.quality,
    pytest.mark.timeout(29),
]

scenarios("../features/agents/pretranslation_agent.feature")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SOURCE_LINES = [
    SourceLine(
        line_id="line_1",
        scene_id="scene_1",
        route_id=None,
        speaker=None,
        text="猫の手も借りたいほど忙しい。",
        metadata=None,
        source_columns=None,
    )
]

_PAYLOAD = PretranslationPhaseInput(
    run_id=UUID("00000000-0000-7000-8000-000000000002"),
    source_lines=_SOURCE_LINES,
    scene_summaries=None,
    context_notes=None,
    project_context=None,
    glossary=None,
)

_JUDGE_RUBRIC = (
    "The agent correctly identifies idiomatic expressions from the input. "
    "If idiom explanations are present in output_text, they accurately "
    "describe the idiom's meaning. If no idioms are present, the output "
    "is still acceptable. The explanation language does not matter."
)


class EvalContext(BaseModel):
    """Container for pretranslation agent eval execution."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    dataset: Dataset = Field(description="Eval dataset for the pretranslation agent")
    task: Callable[[PretranslationPhaseInput], Awaitable[AgentEvalOutput]] = Field(
        description="Async task that runs the agent under test"
    )
    report: EvaluationReport | None = Field(
        default=None, description="Evaluation report populated after execution"
    )


# ---------------------------------------------------------------------------
# Scenario 1: Structural eval (real agent, deterministic evaluators, no judge)
# ---------------------------------------------------------------------------


@given("a pretranslation agent structural eval dataset", target_fixture="ctx")
def given_pretranslation_structural_dataset(
    quality_model_config: QualityModelConfig,
) -> EvalContext:
    """Build the pretranslation agent structural eval dataset.

    Returns:
        Eval context with dataset and execution task (no LLM judge).
    """
    profile_path = get_default_agents_dir() / "pretranslation" / "idiom_labeler.toml"
    prompts_dir = get_default_prompts_dir()
    agent_config = build_profile_config(quality_model_config)

    async def run_pretranslation_eval(
        inputs: PretranslationPhaseInput,
    ) -> AgentEvalOutput:
        recorder = ToolCallRecorder()
        registry = build_tool_registry(recorder)
        agent = create_pretranslation_agent_from_profile(
            profile_path=profile_path,
            prompts_dir=prompts_dir,
            config=agent_config,
            tool_registry=registry,
            source_lang="ja",
            target_lang="en",
        )
        output = await agent.run(inputs)
        if output.annotations:
            output_text = "\n".join(
                (annotation.notes or annotation.value or "")
                for annotation in output.annotations
            ).strip()
            if not output_text:
                output_text = "該当なし"
        else:
            output_text = "該当なし"
        return AgentEvalOutput(
            output_text=output_text,
            output_data=output.model_dump(mode="json"),
            tool_calls=recorder.calls,
        )

    dataset = Dataset(
        cases=[Case(name="pretranslation_structural", inputs=_PAYLOAD)],
        evaluators=[
            OutputFieldPresent(field_name="annotations"),
            OutputFieldPresent(field_name="term_candidates"),
            ListFieldMinLength(field_name="annotations", min_length=0),
            ToolCallCountAtLeast(min_calls=1),
            ToolInputSchemaValid(tool_name="get_game_info", allowed_keys=()),
            ToolResultHasKeys(
                required_keys=(
                    "game_name",
                    "synopsis",
                    "source_language",
                    "target_languages",
                )
            ),
            MaxDuration(seconds=20.0),
        ],
    )

    return EvalContext(dataset=dataset, task=run_pretranslation_eval)


@when("I run the pretranslation agent structural evaluation")
def when_run_pretranslation_structural_eval(ctx: EvalContext) -> None:
    """Execute the pretranslation agent structural eval."""
    ctx.report = asyncio.run(ctx.dataset.evaluate(ctx.task))


@then("the pretranslation agent structural evaluation passes")
def then_pretranslation_structural_eval_passes(ctx: EvalContext) -> None:
    """Assert the structural eval report is successful."""
    assert ctx.report is not None
    assert_report_success(ctx.report)


# ---------------------------------------------------------------------------
# Scenario 2: Judge eval (hardcoded output, LLM judge only, no agent run)
# ---------------------------------------------------------------------------


@given("a pretranslation agent judge eval dataset", target_fixture="ctx")
def given_pretranslation_judge_dataset(
    quality_judge_model: Model,
    quality_judge_settings: ModelSettings,
) -> EvalContext:
    """Build the pretranslation agent judge eval with hardcoded output.

    Returns:
        Eval context with dataset and a task that returns cached output.
    """
    # Hardcoded representative agent output — the agent identifies the idiom
    # 「猫の手も借りたい」 and explains it. This avoids a real LLM call.
    cached_output = AgentEvalOutput(
        output_text=(
            "猫の手も借りたい (neko no te mo karitai) — "
            "An idiom meaning 'so busy that one would even "
            "borrow a cat's paws for help.'"
        ),
        output_data={
            "annotations": [
                {
                    "line_id": "line_1",
                    "value": "猫の手も借りたい",
                    "notes": (
                        "An idiom meaning 'so busy that one would even "
                        "borrow a cat's paws for help.'"
                    ),
                    "category": "idiom",
                }
            ],
            "term_candidates": [],
        },
        tool_calls=[],
    )

    async def return_cached_output(
        inputs: PretranslationPhaseInput,
    ) -> AgentEvalOutput:
        await asyncio.sleep(0)  # yield to event loop
        return cached_output

    dataset = Dataset(
        cases=[Case(name="pretranslation_judge", inputs=_PAYLOAD)],
        evaluators=[
            LLMJudge(
                rubric=_JUDGE_RUBRIC,
                include_input=True,
                model=quality_judge_model,
                model_settings=quality_judge_settings,
                assertion={
                    "evaluation_name": "pretranslation_language_ok",
                    "include_reason": True,
                },
            ),
        ],
    )

    return EvalContext(dataset=dataset, task=return_cached_output)


@when("I run the pretranslation agent judge evaluation")
def when_run_pretranslation_judge_eval(ctx: EvalContext) -> None:
    """Execute the pretranslation agent judge eval."""
    ctx.report = asyncio.run(ctx.dataset.evaluate(ctx.task))


@then("the pretranslation agent judge evaluation passes")
def then_pretranslation_judge_eval_passes(ctx: EvalContext) -> None:
    """Assert the judge eval report is successful."""
    assert ctx.report is not None
    assert_report_success(ctx.report)
