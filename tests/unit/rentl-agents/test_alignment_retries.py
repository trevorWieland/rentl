"""Tests for agent output alignment retries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast
from uuid import UUID

import pytest

from rentl_agents.runtime import ProfileAgent, ProfileAgentConfig
from rentl_agents.wiring import (
    ContextSceneSummarizerAgent,
    EditBasicEditorAgent,
    PretranslationIdiomLabelerAgent,
    QaStyleGuideCriticAgent,
    TranslateDirectTranslatorAgent,
)
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.phases import (
    ContextPhaseInput,
    EditPhaseInput,
    IdiomAnnotation,
    IdiomAnnotationList,
    PretranslationPhaseInput,
    QaPhaseInput,
    SceneSummary,
    StyleGuideReviewLine,
    StyleGuideReviewList,
    StyleGuideRuleViolation,
    TranslatePhaseInput,
    TranslationResultLine,
    TranslationResultList,
)
from rentl_schemas.primitives import QaCategory, QaSeverity
from rentl_schemas.qa import QaIssue


@dataclass
class FakeAgent:
    """Fake profile agent that returns predefined outputs."""

    outputs: list[object]
    contexts: list[object] = field(default_factory=list)
    call_count: int = 0

    def update_context(self, context: object) -> None:
        """Record updated template context."""
        self.contexts.append(context)

    async def run(self, payload: object) -> object:
        """Return the next predefined output."""
        if self.call_count >= len(self.outputs):
            return self.outputs[-1]
        output = self.outputs[self.call_count]
        self.call_count += 1
        return output


def _build_config(max_output_retries: int = 1) -> ProfileAgentConfig:
    return ProfileAgentConfig(
        api_key="test-key",
        model_id="gpt-4o-mini",
        max_output_retries=max_output_retries,
    )


@pytest.mark.asyncio
async def test_translate_retries_on_alignment_error() -> None:
    """Translate agent retries when output IDs do not align."""
    config = _build_config(max_output_retries=1)
    source_lines = [
        SourceLine(line_id="line_1", text="A", scene_id="scene_1"),
        SourceLine(line_id="line_2", text="B", scene_id="scene_1"),
    ]
    payload = TranslatePhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000010"),
        target_language="en",
        source_lines=source_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        pretranslation_annotations=None,
        term_candidates=None,
        glossary=None,
        style_guide=None,
    )
    bad_result = TranslationResultList(
        translations=[TranslationResultLine(line_id="line_1", text="A1")]
    )
    good_result = TranslationResultList(
        translations=[
            TranslationResultLine(line_id="line_1", text="A1"),
            TranslationResultLine(line_id="line_2", text="B1"),
        ]
    )
    agent = TranslateDirectTranslatorAgent(
        profile_agent=cast(
            ProfileAgent[TranslatePhaseInput, TranslationResultList],
            FakeAgent(outputs=[bad_result, good_result]),
        ),
        config=config,
        chunk_size=10,
        source_lang="ja",
        target_lang="en",
    )

    output = await agent.run(payload)

    assert len(output.translated_lines) == 2
    assert output.translated_lines[0].line_id == "line_1"
    assert output.translated_lines[1].line_id == "line_2"


@pytest.mark.asyncio
async def test_translate_raises_after_retry_exhausted() -> None:
    """Translate agent raises after alignment retries are exhausted."""
    config = _build_config(max_output_retries=0)
    source_lines = [
        SourceLine(line_id="line_1", text="A", scene_id="scene_1"),
        SourceLine(line_id="line_2", text="B", scene_id="scene_1"),
    ]
    payload = TranslatePhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000011"),
        target_language="en",
        source_lines=source_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        pretranslation_annotations=None,
        term_candidates=None,
        glossary=None,
        style_guide=None,
    )
    bad_result = TranslationResultList(
        translations=[TranslationResultLine(line_id="line_1", text="A1")]
    )
    agent = TranslateDirectTranslatorAgent(
        profile_agent=cast(
            ProfileAgent[TranslatePhaseInput, TranslationResultList],
            FakeAgent(outputs=[bad_result]),
        ),
        config=config,
        chunk_size=10,
        source_lang="ja",
        target_lang="en",
    )

    with pytest.raises(RuntimeError, match="Alignment error"):
        await agent.run(payload)


@pytest.mark.asyncio
async def test_qa_retries_on_alignment_error() -> None:
    """QA agent retries when review IDs do not align."""
    config = _build_config(max_output_retries=1)
    source_lines = [SourceLine(line_id="line_1", text="A")]
    translated_lines = [TranslatedLine(line_id="line_1", text="A1")]
    payload = QaPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000012"),
        target_language="en",
        source_lines=source_lines,
        translated_lines=translated_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        glossary=None,
        style_guide="Use honorifics",
    )
    bad_review = StyleGuideReviewList(
        reviews=[StyleGuideReviewLine(line_id="line_999", violations=[])]
    )
    good_review = StyleGuideReviewList(
        reviews=[
            StyleGuideReviewLine(
                line_id="line_1",
                violations=[
                    StyleGuideRuleViolation(
                        rule_violated="Rule",
                        explanation="Reason",
                    )
                ],
            )
        ]
    )
    agent = QaStyleGuideCriticAgent(
        profile_agent=cast(
            ProfileAgent[QaPhaseInput, StyleGuideReviewList],
            FakeAgent(outputs=[bad_review, good_review]),
        ),
        config=config,
        chunk_size=10,
        source_lang="ja",
        target_lang="en",
    )

    output = await agent.run(payload)

    assert len(output.issues) == 1
    assert output.issues[0].line_id == "line_1"


@pytest.mark.asyncio
async def test_edit_retries_on_alignment_error() -> None:
    """Edit agent retries when output line_id does not match input."""
    config = _build_config(max_output_retries=1)
    translated_lines = [TranslatedLine(line_id="line_1", text="A1", source_text="A")]
    payload = EditPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000013"),
        target_language="en",
        translated_lines=translated_lines,
        qa_issues=[
            QaIssue(
                issue_id=UUID("00000000-0000-7000-8000-000000000014"),
                line_id="line_1",
                category=QaCategory.STYLE,
                severity=QaSeverity.MINOR,
                message="Test",
            )
        ],
        reviewer_notes=None,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        pretranslation_annotations=None,
        term_candidates=None,
        glossary=None,
        style_guide=None,
    )
    bad_result = TranslationResultLine(line_id="line_999", text="A2")
    good_result = TranslationResultLine(line_id="line_1", text="A2")
    agent = EditBasicEditorAgent(
        profile_agent=cast(
            ProfileAgent[EditPhaseInput, TranslationResultLine],
            FakeAgent(outputs=[bad_result, good_result]),
        ),
        config=config,
        source_lang="ja",
        target_lang="en",
    )

    output = await agent.run(payload)

    assert output.edited_lines[0].line_id == "line_1"
    assert output.edited_lines[0].text == "A2"


@pytest.mark.asyncio
async def test_context_retries_on_alignment_error() -> None:
    """Context agent retries when scene_id does not match input."""
    config = _build_config(max_output_retries=1)
    source_lines = [SourceLine(line_id="line_1", text="A", scene_id="scene_1")]
    payload = ContextPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000015"),
        source_lines=source_lines,
        project_context=None,
        style_guide=None,
        glossary=None,
    )
    bad_summary = SceneSummary(
        scene_id="scene_999",
        summary="Bad",
        characters=["A"],
    )
    good_summary = SceneSummary(
        scene_id="scene_1",
        summary="Good",
        characters=["A"],
    )
    agent = ContextSceneSummarizerAgent(
        profile_agent=cast(
            ProfileAgent[ContextPhaseInput, SceneSummary],
            FakeAgent(outputs=[bad_summary, good_summary]),
        ),
        config=config,
        source_lang="ja",
        target_lang="en",
    )

    output = await agent.run(payload)

    assert output.scene_summaries[0].scene_id == "scene_1"


@pytest.mark.asyncio
async def test_pretranslation_retries_on_invalid_line_id() -> None:
    """Pretranslation agent retries when idiom line_id is not in input."""
    config = _build_config(max_output_retries=1)
    source_lines = [SourceLine(line_id="line_1", text="A", scene_id="scene_1")]
    payload = PretranslationPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000016"),
        source_lines=source_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        glossary=None,
    )
    bad_idiom = IdiomAnnotation(
        line_id="line_999",
        idiom_text="X",
        explanation="Y",
    )
    bad_result = IdiomAnnotationList(idioms=[bad_idiom])
    good_result = IdiomAnnotationList(idioms=[])
    agent = PretranslationIdiomLabelerAgent(
        profile_agent=cast(
            ProfileAgent[PretranslationPhaseInput, IdiomAnnotationList],
            FakeAgent(outputs=[bad_result, good_result]),
        ),
        config=config,
        chunk_size=10,
        source_lang="ja",
        target_lang="en",
    )

    output = await agent.run(payload)

    assert output.annotations == []
