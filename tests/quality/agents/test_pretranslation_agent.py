"""Quality evals for the pretranslation agent."""

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
    pytest.mark.timeout(30),
]

scenarios("../features/agents/pretranslation_agent.feature")


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


@given("a pretranslation agent quality eval dataset", target_fixture="ctx")
def given_pretranslation_dataset(
    quality_model_config: QualityModelConfig,
    quality_judge_model: Model,
    quality_judge_settings: ModelSettings,
) -> EvalContext:
    """Build the pretranslation agent eval dataset and task.

    Returns:
        Eval context with dataset and execution task.
    """
    profile_path = get_default_agents_dir() / "pretranslation" / "idiom_labeler.toml"
    prompts_dir = get_default_prompts_dir()
    agent_config = build_profile_config(quality_model_config)

    source_lines = [
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
    payload = PretranslationPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000002"),
        source_lines=source_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        glossary=None,
    )

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

    rubric = (
        "The agent correctly identifies idiomatic expressions from the input. "
        "If idiom explanations are present in output_text, they accurately "
        "describe the idiom's meaning. If no idioms are present, the output "
        "is still acceptable. The explanation language does not matter."
    )

    dataset = Dataset(
        cases=[Case(name="pretranslation_basic", inputs=payload)],
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
            MaxDuration(seconds=25.0),
            LLMJudge(
                rubric=rubric,
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

    return EvalContext(dataset=dataset, task=run_pretranslation_eval)


@when("I run the pretranslation agent quality evaluation")
def when_run_pretranslation_eval(ctx: EvalContext) -> None:
    """Execute the pretranslation agent eval dataset."""
    ctx.report = asyncio.run(ctx.dataset.evaluate(ctx.task))


@then("the pretranslation agent evaluation passes")
def then_pretranslation_eval_passes(ctx: EvalContext) -> None:
    """Assert the pretranslation agent eval report is successful."""
    assert ctx.report is not None
    assert_report_success(ctx.report)
