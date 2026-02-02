"""Phase input and output schemas for the pipeline."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.primitives import (
    AnnotationId,
    AnnotationType,
    JsonValue,
    LanguageCode,
    LineId,
    NoteId,
    PhaseName,
    RunId,
    SceneId,
)
from rentl_schemas.qa import LineEdit, QaIssue, QaSummary, ReviewerNote


class SceneSummary(BaseSchema):
    """Summary for a scene generated during context phase."""

    scene_id: SceneId = Field(..., description="Scene identifier")
    summary: str = Field(..., min_length=1, description="Scene summary")
    characters: list[str] = Field(..., description="Relevant characters")


class IdiomAnnotation(BaseSchema):
    """Single idiom annotation produced by the Idiom Labeler agent.

    This is the structured output from the idiom labeler, which identifies
    idiomatic expressions requiring special translation handling.
    """

    line_id: LineId = Field(..., description="Line identifier for the annotation")
    idiom_text: str = Field(
        ..., min_length=1, description="The idiomatic expression found"
    )
    idiom_type: str = Field(
        ...,
        pattern=r"^(pun|wordplay|set_phrase|cultural_reference|honorific_nuance|other)$",
        description="Type of idiom (pun, wordplay, set_phrase, etc.)",
    )
    explanation: str = Field(
        ...,
        min_length=1,
        description="Explanation of the idiom's meaning and significance",
    )
    translation_hint: str | None = Field(
        None, description="Optional suggestion for how to handle in translation"
    )


class IdiomAnnotationList(BaseSchema):
    """List of idiom annotations from a single chunk analysis.

    This wrapper schema allows the LLM to return multiple idioms
    found in a batch of lines.
    """

    idioms: list[IdiomAnnotation] = Field(
        default_factory=list,
        description="List of idioms found in the analyzed lines",
    )


class StyleGuideViolation(BaseSchema):
    """Single style guide violation found by the Style Guide Critic agent.

    This is the structured output from the style guide critic, which identifies
    violations of project style guidelines in translations.
    """

    line_id: LineId = Field(..., description="Line identifier for the violation")
    violation_type: str = Field(
        ...,
        pattern=r"^(honorific|formality|terminology|cultural|consistency|other)$",
        description="Type of style violation (honorific, formality, etc.)",
    )
    rule_violated: str = Field(
        ...,
        min_length=1,
        description="The specific style rule that was violated",
    )
    source_text: str = Field(
        ...,
        min_length=1,
        description="The relevant source text being translated",
    )
    translation_text: str = Field(
        ...,
        min_length=1,
        description="The problematic translation text",
    )
    explanation: str = Field(
        ...,
        min_length=1,
        description="Explanation of why this violates the style guide",
    )
    suggestion: str | None = Field(
        None,
        description="Suggested correction for the violation",
    )


class StyleGuideViolationList(BaseSchema):
    """List of style guide violations from a single chunk analysis.

    This wrapper schema allows the LLM to return multiple violations
    found in a batch of translations.
    """

    violations: list[StyleGuideViolation] = Field(
        default_factory=list,
        description="List of style guide violations found",
    )


class TranslationResultLine(BaseSchema):
    """Single translated line in LLM output format.

    This is the structured output from the translator for a single line.
    """

    line_id: LineId = Field(..., description="Line identifier matching the source")
    text: str = Field(..., min_length=1, description="Translated text content")


class TranslationResultList(BaseSchema):
    """List of translation results from a single chunk analysis.

    This wrapper schema allows the LLM to return multiple translated lines
    from a batch of source lines.
    """

    translations: list[TranslationResultLine] = Field(
        ...,
        min_length=1,
        description="List of translated lines",
    )


class ContextNote(BaseSchema):
    """Context note associated with a line or scene."""

    note_id: NoteId = Field(..., description="Context note id")
    line_id: LineId | None = Field(None, description="Associated line identifier")
    scene_id: SceneId | None = Field(None, description="Associated scene identifier")
    note: str = Field(..., min_length=1, description="Context note")


class GlossaryTerm(BaseSchema):
    """Glossary term for translation guidance."""

    term: str = Field(..., min_length=1, description="Source term")
    translation: str = Field(..., min_length=1, description="Preferred translation")
    notes: str | None = Field(None, description="Optional glossary notes")


class PretranslationAnnotation(BaseSchema):
    """Line-level annotation produced during pretranslation."""

    annotation_id: AnnotationId = Field(..., description="Annotation identifier")
    line_id: LineId = Field(..., description="Line identifier for the annotation")
    annotation_type: AnnotationType = Field(..., description="Annotation type")
    value: str | None = Field(None, description="Annotation value if applicable")
    notes: str | None = Field(None, description="Annotation notes")
    metadata: dict[str, JsonValue] | None = Field(
        None, description="Structured annotation metadata"
    )


class TermCandidate(BaseSchema):
    """Terminology candidate extracted from pretranslation."""

    term: str = Field(..., min_length=1, description="Source term")
    notes: str | None = Field(None, description="Terminology notes")
    preferred_translation: str | None = Field(
        None, description="Preferred translation if known"
    )


class ContextPhaseInput(BaseSchema):
    """Input payload for the context phase."""

    run_id: RunId = Field(..., description="Run identifier")
    source_lines: list[SourceLine] = Field(
        ..., min_length=1, description="Source lines"
    )
    project_context: str | None = Field(None, description="High-level project context")
    style_guide: str | None = Field(None, description="Style guide content")
    glossary: list[GlossaryTerm] | None = Field(None, description="Glossary terms")


class ContextPhaseOutput(BaseSchema):
    """Output payload for the context phase."""

    run_id: RunId = Field(..., description="Run identifier")
    phase: PhaseName = Field(PhaseName.CONTEXT, description="Phase name")
    project_context: str | None = Field(
        None, description="Project context generated by the phase"
    )
    style_guide: str | None = Field(
        None, description="Style guide generated by the phase"
    )
    glossary: list[GlossaryTerm] | None = Field(
        None, description="Glossary generated by the phase"
    )
    scene_summaries: list[SceneSummary] = Field(..., description="Scene summaries")
    context_notes: list[ContextNote] = Field(..., description="Context notes")


class PretranslationPhaseInput(BaseSchema):
    """Input payload for the pretranslation phase."""

    run_id: RunId = Field(..., description="Run identifier")
    source_lines: list[SourceLine] = Field(
        ..., min_length=1, description="Source lines"
    )
    scene_summaries: list[SceneSummary] | None = Field(
        None, description="Context scene summaries"
    )
    context_notes: list[ContextNote] | None = Field(None, description="Context notes")
    project_context: str | None = Field(None, description="Project context")
    glossary: list[GlossaryTerm] | None = Field(None, description="Glossary terms")


class PretranslationPhaseOutput(BaseSchema):
    """Output payload for the pretranslation phase."""

    run_id: RunId = Field(..., description="Run identifier")
    phase: PhaseName = Field(PhaseName.PRETRANSLATION, description="Phase name")
    annotations: list[PretranslationAnnotation] = Field(
        ..., description="Pretranslation annotations"
    )
    term_candidates: list[TermCandidate] = Field(
        ..., description="Terminology candidates"
    )


class TranslatePhaseInput(BaseSchema):
    """Input payload for the translate phase."""

    run_id: RunId = Field(..., description="Run identifier")
    target_language: LanguageCode = Field(..., description="Target language code")
    source_lines: list[SourceLine] = Field(
        ..., min_length=1, description="Source lines"
    )
    scene_summaries: list[SceneSummary] | None = Field(
        None, description="Context scene summaries"
    )
    context_notes: list[ContextNote] | None = Field(None, description="Context notes")
    project_context: str | None = Field(None, description="Project context")
    pretranslation_annotations: list[PretranslationAnnotation] | None = Field(
        None, description="Pretranslation annotations"
    )
    term_candidates: list[TermCandidate] | None = Field(
        None, description="Terminology candidates"
    )
    glossary: list[GlossaryTerm] | None = Field(None, description="Glossary terms")
    style_guide: str | None = Field(None, description="Style guide content")


class TranslatePhaseOutput(BaseSchema):
    """Output payload for the translate phase."""

    run_id: RunId = Field(..., description="Run identifier")
    phase: PhaseName = Field(PhaseName.TRANSLATE, description="Phase name")
    target_language: LanguageCode = Field(..., description="Target language code")
    translated_lines: list[TranslatedLine] = Field(
        ..., min_length=1, description="Translated lines"
    )


class QaPhaseInput(BaseSchema):
    """Input payload for the QA phase."""

    run_id: RunId = Field(..., description="Run identifier")
    target_language: LanguageCode = Field(..., description="Target language code")
    source_lines: list[SourceLine] = Field(
        ..., min_length=1, description="Source lines"
    )
    translated_lines: list[TranslatedLine] = Field(
        ..., min_length=1, description="Translated lines"
    )
    scene_summaries: list[SceneSummary] | None = Field(
        None, description="Context scene summaries"
    )
    context_notes: list[ContextNote] | None = Field(None, description="Context notes")
    project_context: str | None = Field(None, description="Project context")
    glossary: list[GlossaryTerm] | None = Field(None, description="Glossary terms")
    style_guide: str | None = Field(None, description="Style guide content")


class QaPhaseOutput(BaseSchema):
    """Output payload for the QA phase."""

    run_id: RunId = Field(..., description="Run identifier")
    phase: PhaseName = Field(PhaseName.QA, description="Phase name")
    target_language: LanguageCode = Field(..., description="Target language code")
    issues: list[QaIssue] = Field(..., description="QA issues")
    summary: QaSummary = Field(..., description="QA summary")


class EditPhaseInput(BaseSchema):
    """Input payload for the edit phase."""

    run_id: RunId = Field(..., description="Run identifier")
    target_language: LanguageCode = Field(..., description="Target language code")
    translated_lines: list[TranslatedLine] = Field(
        ..., min_length=1, description="Translated lines"
    )
    qa_issues: list[QaIssue] | None = Field(None, description="QA issues to address")
    reviewer_notes: list[ReviewerNote] | None = Field(
        None, description="Reviewer notes"
    )
    scene_summaries: list[SceneSummary] | None = Field(
        None, description="Context scene summaries"
    )
    context_notes: list[ContextNote] | None = Field(None, description="Context notes")
    project_context: str | None = Field(None, description="Project context")
    pretranslation_annotations: list[PretranslationAnnotation] | None = Field(
        None, description="Pretranslation annotations"
    )
    term_candidates: list[TermCandidate] | None = Field(
        None, description="Terminology candidates"
    )
    glossary: list[GlossaryTerm] | None = Field(None, description="Glossary terms")
    style_guide: str | None = Field(None, description="Style guide content")


class EditPhaseOutput(BaseSchema):
    """Output payload for the edit phase."""

    run_id: RunId = Field(..., description="Run identifier")
    phase: PhaseName = Field(PhaseName.EDIT, description="Phase name")
    target_language: LanguageCode = Field(..., description="Target language code")
    edited_lines: list[TranslatedLine] = Field(
        ..., min_length=1, description="Edited lines"
    )
    change_log: list[LineEdit] = Field(..., description="Line edit records")
