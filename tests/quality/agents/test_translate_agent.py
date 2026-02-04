"""Quality evals for the translate agent."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

import pytest
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.settings import ModelSettings
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge, MaxDuration
from pydantic_evals.reporting import EvaluationReport
from pytest_bdd import given, scenarios, then, when

from rentl_agents import (
    create_translate_agent_from_profile,
    get_default_agents_dir,
    get_default_prompts_dir,
)
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import SceneSummary, TranslatePhaseInput
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

scenarios("../features/agents/translate_agent.feature")


@dataclass
class EvalContext:
    """Container for translate agent eval execution."""

    dataset: Dataset
    task: Callable[[TranslatePhaseInput], Awaitable[AgentEvalOutput]]
    report: EvaluationReport | None = None


@given("a translate agent quality eval dataset", target_fixture="ctx")
def given_translate_dataset(
    quality_model_config: QualityModelConfig,
    quality_judge_model: OpenAIChatModel,
    quality_judge_settings: ModelSettings,
) -> EvalContext:
    """Build the translate agent eval dataset and task.

    Returns:
        Eval context with dataset and execution task.
    """
    profile_path = get_default_agents_dir() / "translate" / "direct_translator.toml"
    prompts_dir = get_default_prompts_dir()
    agent_config = build_profile_config(quality_model_config)

    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            route_id=None,
            speaker=None,
            text="おはようございます。",
            metadata=None,
            source_columns=None,
        )
    ]
    scene_summaries = [
        SceneSummary(
            scene_id="scene_1",
            summary="朝の挨拶を交わす場面。",
            characters=["主人公"],
        )
    ]
    payload = TranslatePhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000003"),
        target_language="en",
        source_lines=source_lines,
        scene_summaries=scene_summaries,
        context_notes=None,
        project_context=None,
        pretranslation_annotations=None,
        term_candidates=None,
        glossary=None,
        style_guide=None,
    )

    async def run_translate_eval(inputs: TranslatePhaseInput) -> AgentEvalOutput:
        recorder = ToolCallRecorder()
        registry = build_tool_registry(recorder)
        agent = create_translate_agent_from_profile(
            profile_path=profile_path,
            prompts_dir=prompts_dir,
            config=agent_config,
            tool_registry=registry,
            source_lang="ja",
            target_lang="en",
        )
        output = await agent.run(inputs)
        output_text = "\n".join(line.text for line in output.translated_lines)
        return AgentEvalOutput(
            output_text=output_text,
            output_data=output.model_dump(mode="json"),
            tool_calls=recorder.calls,
        )

    # Multi-judge evaluation for different quality dimensions
    # Each judge evaluates a specific aspect of translation quality

    language_rubric = (
        "The translation is written in proper, grammatically correct English. "
        "It reads naturally and fluently as if written by a native speaker. "
        "Score: PASS if language is correct, FAIL if there are "
        "significant grammar or fluency issues."
    )

    accuracy_rubric = (
        "The translation accurately conveys the meaning of the original "
        "Japanese text. No key information is lost or significantly altered. "
        "Score: PASS if meaning is preserved, FAIL if the translation "
        "deviates significantly from the source."
    )

    style_rubric = (
        "The translation matches an appropriate tone and style for a visual "
        "novel/game dialogue. It feels natural for the context and character. "
        "Score: PASS if style is appropriate, FAIL if tone feels wrong "
        "or out of place."
    )

    dataset = Dataset(
        cases=[Case(name="translate_basic", inputs=payload)],
        evaluators=[
            OutputFieldPresent(field_name="translated_lines"),
            ListFieldMinLength(field_name="translated_lines", min_length=1),
            OutputListIdsMatch(
                field_name="translated_lines",
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
            # Multi-judge evaluation: Language/Fluency
            LLMJudge(
                rubric=language_rubric,
                include_input=True,
                model=quality_judge_model,
                model_settings=quality_judge_settings,
                assertion={
                    "evaluation_name": "translate_language_judge",
                    "include_reason": True,
                },
            ),
            # Multi-judge evaluation: Accuracy
            LLMJudge(
                rubric=accuracy_rubric,
                include_input=True,
                model=quality_judge_model,
                model_settings=quality_judge_settings,
                assertion={
                    "evaluation_name": "translate_accuracy_judge",
                    "include_reason": True,
                },
            ),
            # Multi-judge evaluation: Style/Tone
            LLMJudge(
                rubric=style_rubric,
                include_input=True,
                model=quality_judge_model,
                model_settings=quality_judge_settings,
                assertion={
                    "evaluation_name": "translate_style_judge",
                    "include_reason": True,
                },
            ),
        ],
    )

    return EvalContext(dataset=dataset, task=run_translate_eval)


@when("I run the translate agent quality evaluation")
def when_run_translate_eval(ctx: EvalContext) -> None:
    """Execute the translate agent eval dataset."""
    ctx.report = asyncio.run(ctx.dataset.evaluate(ctx.task))


@then("the translate agent evaluation passes")
def then_translate_eval_passes(ctx: EvalContext) -> None:
    """Assert the translate agent eval report is successful."""
    assert ctx.report is not None
    assert_report_success(ctx.report)
