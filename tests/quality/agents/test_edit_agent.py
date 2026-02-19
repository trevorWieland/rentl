"""Quality evals for the edit agent."""

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
    create_edit_agent_from_profile,
    get_default_agents_dir,
    get_default_prompts_dir,
)
from rentl_schemas.io import TranslatedLine
from rentl_schemas.phases import EditPhaseInput
from rentl_schemas.primitives import QaCategory, QaSeverity
from rentl_schemas.qa import QaIssue
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

scenarios("../features/agents/edit_agent.feature")


class EvalContext(BaseModel):
    """Container for edit agent eval execution."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    dataset: Dataset = Field(description="Eval dataset for the edit agent")
    task: Callable[[EditPhaseInput], Awaitable[AgentEvalOutput]] = Field(
        description="Async task that runs the agent under test"
    )
    report: EvaluationReport | None = Field(
        default=None, description="Evaluation report populated after execution"
    )


@given("an edit agent quality eval dataset", target_fixture="ctx")
def given_edit_dataset(
    quality_model_config: QualityModelConfig,
    quality_judge_model: Model,
    quality_judge_settings: ModelSettings,
) -> EvalContext:
    """Build the edit agent eval dataset and task.

    Returns:
        Eval context with dataset and execution task.
    """
    profile_path = get_default_agents_dir() / "edit" / "basic_editor.toml"
    prompts_dir = get_default_prompts_dir()
    agent_config = build_profile_config(quality_model_config)

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
    qa_issues = [
        QaIssue(
            issue_id=UUID("00000000-0000-7000-8000-000000000005"),
            line_id="line_1",
            category=QaCategory.STYLE,
            severity=QaSeverity.MINOR,
            message="Preserve '-san' honorifics in English translations.",
            suggestion="Use 'Tanaka-san'.",
            metadata=None,
        )
    ]
    payload = EditPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000006"),
        target_language="en",
        translated_lines=translated_lines,
        qa_issues=qa_issues,
        reviewer_notes=None,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        pretranslation_annotations=None,
        term_candidates=None,
        glossary=None,
        style_guide=None,
    )

    async def run_edit_eval(inputs: EditPhaseInput) -> AgentEvalOutput:
        recorder = ToolCallRecorder()
        registry = build_tool_registry(recorder)
        agent = create_edit_agent_from_profile(
            profile_path=profile_path,
            prompts_dir=prompts_dir,
            config=agent_config,
            tool_registry=registry,
            source_lang="ja",
            target_lang="en",
        )
        output = await agent.run(inputs)
        output_text = "\n".join(line.text for line in output.edited_lines)
        return AgentEvalOutput(
            output_text=output_text,
            output_data=output.model_dump(mode="json"),
            tool_calls=recorder.calls,
        )

    rubric = (
        "The output_text is written in English and reflects an edited translation "
        "that reasonably addresses the QA issue. Minor errors are acceptable."
    )

    dataset = Dataset(
        cases=[Case(name="edit_basic", inputs=payload)],
        evaluators=[
            OutputFieldPresent(field_name="edited_lines"),
            OutputFieldPresent(field_name="change_log"),
            ListFieldMinLength(field_name="edited_lines", min_length=1),
            ListFieldMinLength(field_name="change_log", min_length=0),
            OutputListIdsMatch(
                field_name="edited_lines",
                id_field="line_id",
                expected_ids=("line_1",),
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
                    "evaluation_name": "edit_language_ok",
                    "include_reason": True,
                },
            ),
        ],
    )

    return EvalContext(dataset=dataset, task=run_edit_eval)


@when("I run the edit agent quality evaluation")
def when_run_edit_eval(ctx: EvalContext) -> None:
    """Execute the edit agent eval dataset."""
    ctx.report = asyncio.run(ctx.dataset.evaluate(ctx.task))


@then("the edit agent evaluation passes")
def then_edit_eval_passes(ctx: EvalContext) -> None:
    """Assert the edit agent eval report is successful."""
    assert ctx.report is not None
    assert_report_success(ctx.report)
