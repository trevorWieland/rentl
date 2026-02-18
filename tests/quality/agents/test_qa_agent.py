"""Quality evals for the QA agent."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge, MaxDuration
from pydantic_evals.reporting import EvaluationReport
from pytest_bdd import given, scenarios, then, when

from rentl_agents import (
    create_qa_agent_from_profile,
    get_default_agents_dir,
    get_default_prompts_dir,
)
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.phases import QaPhaseInput
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

pytestmark = pytest.mark.quality

scenarios("../features/agents/qa_agent.feature")


@dataclass
class EvalContext:
    """Container for QA agent eval execution."""

    dataset: Dataset
    task: Callable[[QaPhaseInput], Awaitable[AgentEvalOutput]]
    report: EvaluationReport | None = None


@given("a QA agent quality eval dataset", target_fixture="ctx")
def given_qa_dataset(
    quality_model_config: QualityModelConfig,
    quality_judge_model: Model,
    quality_judge_settings: ModelSettings,
) -> EvalContext:
    """Build the QA agent eval dataset and task.

    Returns:
        Eval context with dataset and execution task.
    """
    profile_path = get_default_agents_dir() / "qa" / "style_guide_critic.toml"
    prompts_dir = get_default_prompts_dir()
    agent_config = build_profile_config(quality_model_config)

    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            route_id=None,
            speaker=None,
            text="田中さん、おはようございます。",
            metadata=None,
            source_columns=None,
        )
    ]
    translated_lines = [
        TranslatedLine(
            line_id="line_1",
            scene_id="scene_1",
            route_id=None,
            speaker=None,
            source_text="田中さん、おはようございます。",
            text="Good morning, Mr. Tanaka.",
            metadata=None,
            source_columns=None,
        )
    ]
    style_guide = (
        "Use honorifics in English translations. Preserve '-san' when present."
    )
    payload = QaPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000004"),
        target_language="en",
        source_lines=source_lines,
        translated_lines=translated_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        glossary=None,
        style_guide=style_guide,
    )

    async def run_qa_eval(inputs: QaPhaseInput) -> AgentEvalOutput:
        recorder = ToolCallRecorder()
        registry = build_tool_registry(recorder)
        agent = create_qa_agent_from_profile(
            profile_path=profile_path,
            prompts_dir=prompts_dir,
            config=agent_config,
            tool_registry=registry,
            source_lang="ja",
            target_lang="en",
        )
        output = await agent.run(inputs)
        if output.issues:
            output_text = "\n".join(issue.message for issue in output.issues)
        else:
            output_text = "No violations found."
        return AgentEvalOutput(
            output_text=output_text,
            output_data=output.model_dump(mode="json"),
            tool_calls=recorder.calls,
        )

    rubric = (
        "The output_text is written in clear English and describes any style "
        "guide violations that were found. If no violations are present, the "
        "output may indicate that none were found."
    )

    dataset = Dataset(
        cases=[Case(name="qa_basic", inputs=payload)],
        evaluators=[
            OutputFieldPresent(field_name="issues"),
            OutputFieldPresent(field_name="summary"),
            ListFieldMinLength(field_name="issues", min_length=0),
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
                    "evaluation_name": "qa_language_ok",
                    "include_reason": True,
                },
            ),
        ],
    )

    return EvalContext(dataset=dataset, task=run_qa_eval)


@when("I run the QA agent quality evaluation")
def when_run_qa_eval(ctx: EvalContext) -> None:
    """Execute the QA agent eval dataset."""
    ctx.report = asyncio.run(ctx.dataset.evaluate(ctx.task))


@then("the QA agent evaluation passes")
def then_qa_eval_passes(ctx: EvalContext) -> None:
    """Assert the QA agent eval report is successful."""
    assert ctx.report is not None
    assert_report_success(ctx.report)
