"""Quality eval for required-tool retry recovery mechanism."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, Field
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import MaxDuration
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
    RequiredToolCalledBeforeOutput,
    ToolCallCountAtLeast,
    assert_report_success,
)
from tests.quality.agents.quality_harness import (
    QualityModelConfig,
    build_profile_config,
)
from tests.quality.agents.tool_spy import ToolCallRecorder, build_tool_registry

pytestmark = pytest.mark.quality

scenarios("../features/agents/retry_recovery.feature")


class EvalContext(BaseModel):
    """Container for retry recovery eval execution."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    dataset: Dataset = Field(description="Eval dataset for retry recovery")
    task: Callable[[ContextPhaseInput], Awaitable[AgentEvalOutput]] = Field(
        description="Async task that runs the agent under test"
    )
    report: EvaluationReport | None = Field(
        default=None, description="Evaluation report populated after execution"
    )


@given("a retry recovery quality eval dataset", target_fixture="ctx")
def given_recovery_dataset(
    quality_model_config: QualityModelConfig,
) -> EvalContext:
    """Build the retry recovery eval dataset and task.

    Returns:
        Eval context with dataset and execution task.
    """
    profile_path = get_default_agents_dir() / "context" / "scene_summarizer.toml"
    prompts_dir = get_default_prompts_dir()

    # Override default config to allow retries for recovery
    base_config = build_profile_config(quality_model_config)
    agent_config = base_config.model_copy(
        update={
            "max_output_retries": 3,
            "max_requests_per_run": 8,
        }
    )

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
        run_id=UUID("00000000-0000-7000-8000-000000000002"),
        source_lines=source_lines,
        project_context="Test project context for recovery eval",
        style_guide=None,
        glossary=None,
    )

    async def run_recovery_eval(inputs: ContextPhaseInput) -> AgentEvalOutput:
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

    dataset = Dataset(
        cases=[Case(name="recovery_enforcement", inputs=payload)],
        evaluators=[
            RequiredToolCalledBeforeOutput(required_tool="get_game_info"),
            ToolCallCountAtLeast(min_calls=1),
            OutputFieldPresent(field_name="scene_summaries"),
            ListFieldMinLength(field_name="scene_summaries", min_length=1),
            MaxDuration(seconds=30.0),
        ],
    )

    return EvalContext(dataset=dataset, task=run_recovery_eval)


@when("I run the retry recovery quality evaluation")
def when_run_recovery_eval(ctx: EvalContext) -> None:
    """Execute the retry recovery eval dataset."""
    ctx.report = asyncio.run(ctx.dataset.evaluate(ctx.task))


@then("the retry recovery evaluation passes")
def then_recovery_eval_passes(ctx: EvalContext) -> None:
    """Assert the retry recovery eval report is successful."""
    assert ctx.report is not None
    assert_report_success(ctx.report)
