"""Phase explanation and documentation module."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import PhaseName


class PhaseInfo(BaseSchema):
    """Information about a pipeline phase."""

    name: PhaseName = Field(..., description="Phase name")
    description: str = Field(..., min_length=1, description="Phase description")
    inputs: list[str] = Field(..., description="Expected inputs for this phase")
    outputs: list[str] = Field(..., description="Outputs produced by this phase")
    prerequisites: list[str] = Field(
        ..., description="Prerequisites before running this phase"
    )
    config_options: list[str] = Field(..., description="Relevant configuration options")


# Phase registry with complete information for all 7 phases
_PHASE_REGISTRY: dict[PhaseName, PhaseInfo] = {
    PhaseName.INGEST: PhaseInfo(
        name=PhaseName.INGEST,
        description="Parse and validate source files into a structured scene database",
        inputs=[
            "Source files (CSV, JSONL, TXT)",
            "Ingest configuration (format, file paths)",
        ],
        outputs=[
            "Scene database with parsed lines",
            "Source file metadata",
            "Ingest validation report",
        ],
        prerequisites=[
            "Valid source files in the configured format",
            "Workspace directory structure initialized",
        ],
        config_options=[
            "pipeline.phases[phase=ingest].enabled",
            "pipeline.phases[phase=ingest].model",
            "ingest.format (csv|jsonl|txt)",
            "ingest.source_files",
        ],
    ),
    PhaseName.CONTEXT: PhaseInfo(
        name=PhaseName.CONTEXT,
        description=(
            "Analyze scenes to extract context information "
            "(speakers, location, relationships)"
        ),
        inputs=[
            "Scene database from ingest phase",
            "Context extraction prompts",
        ],
        outputs=[
            "Context annotations per scene (speakers, location, etc.)",
            "Context analysis summary",
        ],
        prerequisites=[
            "Ingest phase complete",
            "LLM endpoint configured and accessible",
        ],
        config_options=[
            "pipeline.phases[phase=context].enabled",
            "pipeline.phases[phase=context].model",
            "context.extract_speakers",
            "context.extract_location",
        ],
    ),
    PhaseName.PRETRANSLATION: PhaseInfo(
        name=PhaseName.PRETRANSLATION,
        description=(
            "Apply translation memory and glossary to pre-fill known translations"
        ),
        inputs=[
            "Scene database from previous phases",
            "Translation memory (TM) entries",
            "Glossary terms",
        ],
        outputs=[
            "Pre-translated lines (exact matches from TM/glossary)",
            "Fuzzy match suggestions",
            "Pretranslation coverage report",
        ],
        prerequisites=[
            "Ingest phase complete",
            "Translation memory or glossary configured (if applicable)",
        ],
        config_options=[
            "pipeline.phases[phase=pretranslation].enabled",
            "pipeline.phases[phase=pretranslation].model",
            "pretranslation.tm_threshold",
            "pretranslation.use_glossary",
        ],
    ),
    PhaseName.TRANSLATE: PhaseInfo(
        name=PhaseName.TRANSLATE,
        description="Generate translations for lines not covered by pretranslation",
        inputs=[
            "Scene database with context and pretranslation data",
            "Target language configuration",
            "Translation prompts and guidelines",
        ],
        outputs=[
            "Translated lines for the target language",
            "Translation confidence scores",
            "LLM usage metrics",
        ],
        prerequisites=[
            "Ingest phase complete",
            "Target language configured",
            "LLM endpoint configured and accessible",
        ],
        config_options=[
            "pipeline.phases[phase=translate].enabled",
            "pipeline.phases[phase=translate].model",
            "project.target_languages",
            "translation.style_guide",
        ],
    ),
    PhaseName.QA: PhaseInfo(
        name=PhaseName.QA,
        description=(
            "Quality assurance checks on translations "
            "(consistency, terminology, length)"
        ),
        inputs=[
            "Translated lines from translate phase",
            "Glossary and style guide rules",
        ],
        outputs=[
            "QA issues flagged per line (terminology, length, consistency)",
            "QA summary report",
        ],
        prerequisites=[
            "Translate phase complete for target language",
        ],
        config_options=[
            "pipeline.phases[phase=qa].enabled",
            "pipeline.phases[phase=qa].model",
            "qa.check_terminology",
            "qa.check_length",
            "qa.check_consistency",
        ],
    ),
    PhaseName.EDIT: PhaseInfo(
        name=PhaseName.EDIT,
        description=(
            "Interactive editing session for translators to review "
            "and refine translations"
        ),
        inputs=[
            "Translated lines with QA annotations",
            "Context information",
        ],
        outputs=[
            "Edited and approved translations",
            "Edit history and revision log",
        ],
        prerequisites=[
            "Translate phase complete",
            "QA phase complete (recommended)",
        ],
        config_options=[
            "pipeline.phases[phase=edit].enabled",
            "edit.auto_approve_threshold",
        ],
    ),
    PhaseName.EXPORT: PhaseInfo(
        name=PhaseName.EXPORT,
        description="Export final translations to output files in the desired format",
        inputs=[
            "Approved translations (edited or auto-approved)",
            "Export format configuration",
        ],
        outputs=[
            "Translated output files (CSV, JSONL, TXT)",
            "Export validation report",
        ],
        prerequisites=[
            "Translate phase complete for target language",
            "All required edits completed (if edit phase enabled)",
        ],
        config_options=[
            "pipeline.phases[phase=export].enabled",
            "export.format (csv|jsonl|txt)",
            "export.output_path",
            "export.untranslated_policy (error|warn|allow)",
        ],
    ),
}


def get_phase_info(phase_name: str | PhaseName) -> PhaseInfo:
    """Get detailed information about a pipeline phase.

    Args:
        phase_name: The name of the phase (string or PhaseName enum)

    Returns:
        PhaseInfo: Detailed information about the phase

    Raises:
        ValueError: If the phase name is invalid
    """
    # Convert string to PhaseName if needed
    if isinstance(phase_name, str):
        try:
            phase_name = PhaseName(phase_name)
        except ValueError:
            valid_phases = ", ".join([p.value for p in PhaseName])
            raise ValueError(
                f"Invalid phase name '{phase_name}'. Valid phases: {valid_phases}"
            ) from None

    return _PHASE_REGISTRY[phase_name]


def list_phases() -> list[tuple[PhaseName, str]]:
    """List all pipeline phases with brief descriptions.

    Returns:
        list[tuple[PhaseName, str]]: List of (phase_name, one_line_description) tuples
    """
    return [(phase, info.description) for phase, info in _PHASE_REGISTRY.items()]
