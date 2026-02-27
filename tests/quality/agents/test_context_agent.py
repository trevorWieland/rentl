"""Quality evals for the context agent."""

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
    create_context_agent_from_profile,
    get_default_agents_dir,
    get_default_prompts_dir,
)
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import ContextPhaseInput
from tests.quality.agents.eval_types import AgentEvalOutput
from tests.quality.agents.evaluators import (
    ListFieldMinLength,
    OutputFieldPresent,
    OutputListIdsMatch,
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

pytestmark = pytest.mark.quality

scenarios("../features/agents/context_agent.feature")


class EvalContext(BaseModel):
    """Container for context agent eval execution."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    dataset: Dataset = Field(description="Eval dataset for the context agent")
    task: Callable[[ContextPhaseInput], Awaitable[AgentEvalOutput]] = Field(
        description="Async task that runs the agent under test"
    )
    report: EvaluationReport | None = Field(
        default=None, description="Evaluation report populated after execution"
    )


@given("a context agent quality eval dataset", target_fixture="ctx")
def given_context_dataset(
    quality_model_config: QualityModelConfig,
    quality_judge_model: Model,
    quality_judge_settings: ModelSettings,
) -> EvalContext:
    """Build the context agent eval dataset and task.

    Returns:
        Eval context with dataset and execution task.
    """
    profile_path = get_default_agents_dir() / "context" / "scene_summarizer.toml"
    prompts_dir = get_default_prompts_dir()
    agent_config = build_profile_config(quality_model_config)

    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            route_id=None,
            speaker=None,
            text="こんにちは。",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_2",
            scene_id="scene_1",
            route_id=None,
            speaker=None,
            text="今日はいい天気ですね。",
            metadata=None,
            source_columns=None,
        ),
    ]
    payload = ContextPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000001"),
        source_lines=source_lines,
        project_context="Test project context",
        style_guide=None,
        glossary=None,
    )

    async def run_context_eval(inputs: ContextPhaseInput) -> AgentEvalOutput:
        recorder = ToolCallRecorder()
        registry = build_tool_registry(recorder)
        agent = create_context_agent_from_profile(
            profile_path=profile_path,
            prompts_dir=prompts_dir,
            config=agent_config,
            tool_registry=registry,
            source_lang="ja",
            target_lang="en",
        )
        output = await agent.run(inputs)
        summary_text = (
            output.scene_summaries[0].summary
            if output.scene_summaries
            else "No summary"
        )
        return AgentEvalOutput(
            output_text=summary_text,
            output_data=output.model_dump(mode="json"),
            tool_calls=recorder.calls,
        )

    rubric = (
        "The output_text is a concise scene summary written primarily in Japanese. "
        "It should reflect the events in the input lines. Minor errors are acceptable."
    )

    dataset = Dataset(
        cases=[Case(name="context_basic", inputs=payload)],
        evaluators=[
            OutputFieldPresent(field_name="scene_summaries"),
            ListFieldMinLength(field_name="scene_summaries", min_length=1),
            OutputListIdsMatch(
                field_name="scene_summaries",
                id_field="scene_id",
                expected_ids=("scene_1",),
            ),
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
            MaxDuration(seconds=25.0),
            LLMJudge(
                rubric=rubric,
                include_input=True,
                model=quality_judge_model,
                model_settings=quality_judge_settings,
                assertion={
                    "evaluation_name": "context_language_ok",
                    "include_reason": True,
                },
            ),
        ],
    )

    return EvalContext(dataset=dataset, task=run_context_eval)


@when("I run the context agent quality evaluation")
def when_run_context_eval(ctx: EvalContext) -> None:
    """Execute the context agent eval dataset."""
    ctx.report = asyncio.run(ctx.dataset.evaluate(ctx.task))


@then("the context agent evaluation passes")
def then_context_eval_passes(ctx: EvalContext) -> None:
    """Assert the context agent eval report is successful."""
    assert ctx.report is not None
    assert_report_success(ctx.report)
