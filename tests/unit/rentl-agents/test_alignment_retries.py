"""Tests for agent output alignment retries."""

from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, Field

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
    IdiomReviewLine,
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


class FakeAgent(BaseModel):
    """Fake profile agent that returns predefined outputs."""

    model_config = ConfigDict(extra="forbid")

    outputs: list[BaseModel] = Field(
        description="Predefined outputs to return in sequence"
    )
    contexts: list[BaseModel] = Field(
        default_factory=list,
        description="Recorded template contexts from update_context",
    )
    call_count: int = Field(default=0, description="Number of run() calls made so far")

    def update_context(self, context: BaseModel) -> None:
        """Record updated template context."""
        self.contexts.append(context)

    async def run(self, payload: BaseModel) -> BaseModel:
        """Return the next predefined output."""
        if self.call_count >= len(self.outputs):
            return self.outputs[-1]
        output = self.outputs[self.call_count]
        self.call_count += 1
        return output


def _build_config(max_output_retries: int = 1) -> ProfileAgentConfig:
    return ProfileAgentConfig(
        api_key="test-key",
        model_id="gpt-5-nano",
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
async def test_pretranslation_retries_on_extra_ids() -> None:
    """Pretranslation agent retries when review line_id is not in input (extra IDs)."""
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
    idiom = IdiomAnnotation(idiom_text="X", explanation="Y")
    bad_result = IdiomAnnotationList(
        reviews=[
            IdiomReviewLine(line_id="line_999", idioms=[idiom]),
            IdiomReviewLine(line_id="line_1", idioms=[idiom]),
        ]
    )
    good_result = IdiomAnnotationList(
        reviews=[IdiomReviewLine(line_id="line_1", idioms=[idiom])]
    )
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

    assert len(output.annotations) == 1
    assert output.annotations[0].line_id == "line_1"


@pytest.mark.asyncio
async def test_pretranslation_retries_on_missing_ids() -> None:
    """Pretranslation agent retries when output is missing input line_ids."""
    config = _build_config(max_output_retries=1)
    source_lines = [
        SourceLine(line_id="line_1", text="A", scene_id="scene_1"),
        SourceLine(line_id="line_2", text="B", scene_id="scene_1"),
    ]
    payload = PretranslationPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000017"),
        source_lines=source_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        glossary=None,
    )
    # Only has line_1 review, missing line_2
    missing_result = IdiomAnnotationList(
        reviews=[
            IdiomReviewLine(
                line_id="line_1",
                idioms=[IdiomAnnotation(idiom_text="X", explanation="Y")],
            )
        ]
    )
    # Complete review set
    good_result = IdiomAnnotationList(
        reviews=[
            IdiomReviewLine(
                line_id="line_1",
                idioms=[IdiomAnnotation(idiom_text="X", explanation="Y")],
            ),
            IdiomReviewLine(
                line_id="line_2",
                idioms=[IdiomAnnotation(idiom_text="Z", explanation="W")],
            ),
        ]
    )
    agent = PretranslationIdiomLabelerAgent(
        profile_agent=cast(
            ProfileAgent[PretranslationPhaseInput, IdiomAnnotationList],
            FakeAgent(outputs=[missing_result, good_result]),
        ),
        config=config,
        chunk_size=10,
        source_lang="ja",
        target_lang="en",
    )

    output = await agent.run(payload)

    assert len(output.annotations) == 2
    annotation_ids = {a.line_id for a in output.annotations}
    assert annotation_ids == {"line_1", "line_2"}


@pytest.mark.asyncio
async def test_pretranslation_retries_on_extra_and_missing_ids() -> None:
    """Pretranslation agent retries when output has both extra and missing IDs."""
    config = _build_config(max_output_retries=1)
    source_lines = [
        SourceLine(line_id="line_1", text="A", scene_id="scene_1"),
        SourceLine(line_id="line_2", text="B", scene_id="scene_1"),
    ]
    payload = PretranslationPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000018"),
        source_lines=source_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        glossary=None,
    )
    idiom = IdiomAnnotation(idiom_text="X", explanation="Y")
    # Has extra line_999, missing line_2
    bad_result = IdiomAnnotationList(
        reviews=[
            IdiomReviewLine(line_id="line_1", idioms=[idiom]),
            IdiomReviewLine(line_id="line_999", idioms=[idiom]),
        ]
    )
    good_result = IdiomAnnotationList(
        reviews=[
            IdiomReviewLine(line_id="line_1", idioms=[idiom]),
            IdiomReviewLine(
                line_id="line_2",
                idioms=[IdiomAnnotation(idiom_text="Z", explanation="W")],
            ),
        ]
    )
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

    assert len(output.annotations) == 2
    annotation_ids = {a.line_id for a in output.annotations}
    assert annotation_ids == {"line_1", "line_2"}


@pytest.mark.asyncio
async def test_pretranslation_sparse_output_passes_alignment() -> None:
    """Pretranslation agent accepts sparse output where some lines have no idioms."""
    config = _build_config(max_output_retries=0)
    source_lines = [
        SourceLine(line_id="line_1", text="A", scene_id="scene_1"),
        SourceLine(line_id="line_2", text="B", scene_id="scene_1"),
        SourceLine(line_id="line_3", text="C", scene_id="scene_1"),
    ]
    payload = PretranslationPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000020"),
        source_lines=source_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        glossary=None,
    )
    # Only line_2 has an idiom, others have empty lists
    result = IdiomAnnotationList(
        reviews=[
            IdiomReviewLine(line_id="line_1", idioms=[]),
            IdiomReviewLine(
                line_id="line_2",
                idioms=[IdiomAnnotation(idiom_text="X", explanation="Y")],
            ),
            IdiomReviewLine(line_id="line_3", idioms=[]),
        ]
    )
    agent = PretranslationIdiomLabelerAgent(
        profile_agent=cast(
            ProfileAgent[PretranslationPhaseInput, IdiomAnnotationList],
            FakeAgent(outputs=[result]),
        ),
        config=config,
        chunk_size=10,
        source_lang="ja",
        target_lang="en",
    )

    output = await agent.run(payload)

    # Only 1 annotation from line_2 (the others had empty idiom lists)
    assert len(output.annotations) == 1
    assert output.annotations[0].line_id == "line_2"


@pytest.mark.asyncio
async def test_pretranslation_raises_after_retry_exhausted() -> None:
    """Pretranslation agent raises after alignment retries are exhausted."""
    config = _build_config(max_output_retries=0)
    source_lines = [
        SourceLine(line_id="line_1", text="A", scene_id="scene_1"),
        SourceLine(line_id="line_2", text="B", scene_id="scene_1"),
    ]
    payload = PretranslationPhaseInput(
        run_id=UUID("00000000-0000-7000-8000-000000000019"),
        source_lines=source_lines,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        glossary=None,
    )
    bad_result = IdiomAnnotationList(
        reviews=[
            IdiomReviewLine(
                line_id="line_999",
                idioms=[IdiomAnnotation(idiom_text="X", explanation="Y")],
            )
        ]
    )
    agent = PretranslationIdiomLabelerAgent(
        profile_agent=cast(
            ProfileAgent[PretranslationPhaseInput, IdiomAnnotationList],
            FakeAgent(outputs=[bad_result]),
        ),
        config=config,
        chunk_size=10,
        source_lang="ja",
        target_lang="en",
    )

    with pytest.raises(RuntimeError, match="Alignment error"):
        await agent.run(payload)
