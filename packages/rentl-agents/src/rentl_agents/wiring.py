"""Profile agent factory for creating orchestrator-ready agents.

This module provides factory functions to create phase agents from TOML profiles
and wire them to the pipeline orchestrator.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rentl_agents.context.scene import (
    format_scene_lines,
    group_lines_by_scene,
)
from rentl_agents.layers import load_layer_registry
from rentl_agents.profiles.loader import load_agent_profile
from rentl_agents.runtime import ProfileAgent, ProfileAgentConfig
from rentl_agents.templates import TemplateContext
from rentl_agents.tools.registry import ToolRegistry, get_default_registry
from rentl_schemas.io import TranslatedLine
from rentl_schemas.phases import (
    ContextPhaseInput,
    ContextPhaseOutput,
    EditPhaseInput,
    EditPhaseOutput,
    IdiomAnnotation,
    IdiomAnnotationList,
    PretranslationPhaseInput,
    PretranslationPhaseOutput,
    QaPhaseInput,
    QaPhaseOutput,
    SceneSummary,
    StyleGuideViolationList,
    TranslatePhaseInput,
    TranslatePhaseOutput,
    TranslationResultLine,
    TranslationResultList,
)
from rentl_schemas.primitives import LanguageCode, PhaseName, QaSeverity
from rentl_schemas.qa import LineEdit, QaIssue

if TYPE_CHECKING:
    pass


class ContextSceneSummarizerAgent:
    """Context phase agent that summarizes scenes using a ProfileAgent.

    This agent:
    1. Validates that all lines have scene_id (required by SceneSummarizer)
    2. Groups lines by scene
    3. Runs ProfileAgent for each scene to produce SceneSummary
    4. Merges results into ContextPhaseOutput
    """

    def __init__(
        self,
        profile_agent: ProfileAgent[ContextPhaseInput, SceneSummary],
        config: ProfileAgentConfig,
        source_lang: LanguageCode = "ja",
        target_lang: LanguageCode = "en",
    ) -> None:
        """Initialize the context scene summarizer agent.

        Args:
            profile_agent: Underlying ProfileAgent for scene summarization.
            config: Runtime configuration.
            source_lang: Source language name for prompts.
            target_lang: Target language name for prompts.
        """
        self._profile_agent = profile_agent
        self._config = config
        self._source_lang = source_lang
        self._target_lang = target_lang

    async def run(self, payload: ContextPhaseInput) -> ContextPhaseOutput:
        """Execute context phase by summarizing each scene.

        Args:
            payload: Context phase input with source lines.

        Returns:
            Context phase output with scene summaries.
        """
        from rentl_agents.context.scene import validate_scene_input

        # Validate all lines have scene_id
        validate_scene_input(payload.source_lines)

        # Group lines by scene
        scene_groups = group_lines_by_scene(payload.source_lines)

        # Summarize each scene
        summaries: list[SceneSummary] = []
        for scene_id, lines in scene_groups.items():
            # Update template context for this scene
            scene_lines_text = format_scene_lines(lines)
            context = TemplateContext(
                root_variables={},
                phase_variables={
                    "source_lang": self._source_lang,
                    "target_lang": self._target_lang,
                },
                agent_variables={
                    "scene_id": scene_id,
                    "line_count": str(len(lines)),
                    "scene_lines": scene_lines_text,
                },
            )
            self._profile_agent.update_context(context)

            # Run the profile agent for this scene
            # Note: ProfileAgent returns SceneSummary directly
            summary = await self._profile_agent.run(payload)
            summaries.append(summary)

        return ContextPhaseOutput(
            run_id=payload.run_id,
            phase=PhaseName.CONTEXT,
            scene_summaries=summaries,
            context_notes=[],
            project_context=payload.project_context,
            style_guide=payload.style_guide,
            glossary=payload.glossary,
        )


def create_context_agent_from_profile(
    profile_path: Path,
    prompts_dir: Path,
    config: ProfileAgentConfig,
    tool_registry: ToolRegistry | None = None,
    source_lang: LanguageCode = "ja",
    target_lang: LanguageCode = "en",
) -> ContextSceneSummarizerAgent:
    """Create a context phase agent from a TOML profile.

    Args:
        profile_path: Path to the agent profile TOML file.
        prompts_dir: Path to the prompts directory (containing root.toml, phases/).
        config: Runtime configuration (API key, model settings, etc.).
        tool_registry: Tool registry to use. Defaults to the default registry.
        source_lang: Source language name for prompts.
        target_lang: Target language name for prompts.

    Returns:
        Context phase agent ready for orchestrator.

    Raises:
        ValueError: If profile is not for context phase.
    """
    # Load the profile
    profile = load_agent_profile(profile_path)

    # Verify it's a context phase agent
    if profile.meta.phase != PhaseName.CONTEXT:
        raise ValueError(
            f"Profile {profile.meta.name} is for phase {profile.meta.phase.value}, "
            f"expected context"
        )

    # Load prompt layers
    layer_registry = load_layer_registry(prompts_dir)

    # Get tool registry
    if tool_registry is None:
        tool_registry = get_default_registry()

    # Create the ProfileAgent
    profile_agent: ProfileAgent[ContextPhaseInput, SceneSummary] = ProfileAgent(
        profile=profile,
        output_type=SceneSummary,
        layer_registry=layer_registry,
        tool_registry=tool_registry,
        config=config,
    )

    # Wrap in ContextSceneSummarizerAgent
    return ContextSceneSummarizerAgent(
        profile_agent=profile_agent,
        config=config,
        source_lang=source_lang,
        target_lang=target_lang,
    )


def get_default_prompts_dir() -> Path:
    """Get the default prompts directory path.

    Returns:
        Path to the prompts directory in rentl-agents package.
    """
    # Navigate from this file to the package prompts directory
    # File is in: packages/rentl-agents/src/rentl_agents/wiring.py
    # Prompts are in: packages/rentl-agents/prompts/
    package_root = Path(__file__).parent.parent.parent  # Up to rentl-agents/
    return package_root / "prompts"


def get_default_agents_dir() -> Path:
    """Get the default agents directory path.

    Returns:
        Path to the agents directory in rentl-agents package.
    """
    # Navigate from this file to the package agents directory
    # File is in: packages/rentl-agents/src/rentl_agents/wiring.py
    # Agents are in: packages/rentl-agents/agents/
    package_root = Path(__file__).parent.parent.parent  # Up to rentl-agents/
    return package_root / "agents"


class PretranslationIdiomLabelerAgent:
    """Pretranslation phase agent that identifies idioms using a ProfileAgent.

    This agent:
    1. Chunks source lines into batches for processing
    2. Runs ProfileAgent for each chunk to identify idioms
    3. Merges results into PretranslationPhaseOutput
    """

    def __init__(
        self,
        profile_agent: ProfileAgent[PretranslationPhaseInput, IdiomAnnotationList],
        config: ProfileAgentConfig,
        chunk_size: int = 10,
        source_lang: LanguageCode = "ja",
        target_lang: LanguageCode = "en",
    ) -> None:
        """Initialize the pretranslation idiom labeler agent.

        Args:
            profile_agent: Underlying ProfileAgent for idiom identification.
            config: Runtime configuration.
            chunk_size: Number of lines per processing chunk.
            source_lang: Source language name for prompts.
            target_lang: Target language name for prompts.
        """
        self._profile_agent = profile_agent
        self._config = config
        self._chunk_size = chunk_size
        self._source_lang = source_lang
        self._target_lang = target_lang

    async def run(self, payload: PretranslationPhaseInput) -> PretranslationPhaseOutput:
        """Execute pretranslation phase by identifying idioms in chunks.

        Args:
            payload: Pretranslation phase input with source lines.

        Returns:
            Pretranslation phase output with idiom annotations.
        """
        from rentl_agents.pretranslation.lines import (
            chunk_lines,
            format_lines_for_prompt,
            get_scene_summary_for_lines,
            merge_idiom_annotations,
        )

        # Chunk lines for batch processing
        chunks = chunk_lines(payload.source_lines, self._chunk_size)

        # Process each chunk
        all_idioms: list[IdiomAnnotation] = []
        for chunk in chunks:
            # Format lines for prompt
            source_lines_text = format_lines_for_prompt(chunk)
            scene_summary_text = get_scene_summary_for_lines(
                chunk, payload.scene_summaries
            )

            # Update template context for this chunk
            context = TemplateContext(
                root_variables={},
                phase_variables={
                    "source_lang": self._source_lang,
                    "target_lang": self._target_lang,
                },
                agent_variables={
                    "source_lines": source_lines_text,
                    "scene_summary": scene_summary_text,
                    "line_count": str(len(chunk)),
                },
            )
            self._profile_agent.update_context(context)

            # Run the profile agent for this chunk
            # ProfileAgent returns IdiomAnnotationList with all idioms found
            result = await self._profile_agent.run(payload)
            all_idioms.extend(result.idioms)

        return merge_idiom_annotations(payload.run_id, all_idioms)


def create_pretranslation_agent_from_profile(
    profile_path: Path,
    prompts_dir: Path,
    config: ProfileAgentConfig,
    tool_registry: ToolRegistry | None = None,
    chunk_size: int = 10,
    source_lang: LanguageCode = "ja",
    target_lang: LanguageCode = "en",
) -> PretranslationIdiomLabelerAgent:
    """Create a pretranslation phase agent from a TOML profile.

    Args:
        profile_path: Path to the agent profile TOML file.
        prompts_dir: Path to the prompts directory (containing root.toml, phases/).
        config: Runtime configuration (API key, model settings, etc.).
        tool_registry: Tool registry to use. Defaults to the default registry.
        chunk_size: Number of lines per processing chunk.
        source_lang: Source language name for prompts.
        target_lang: Target language name for prompts.

    Returns:
        Pretranslation phase agent ready for orchestrator.

    Raises:
        ValueError: If profile is not for pretranslation phase.
    """
    # Load the profile
    profile = load_agent_profile(profile_path)

    # Verify it's a pretranslation phase agent
    if profile.meta.phase != PhaseName.PRETRANSLATION:
        raise ValueError(
            f"Profile {profile.meta.name} is for phase {profile.meta.phase.value}, "
            f"expected pretranslation"
        )

    # Load prompt layers
    layer_registry = load_layer_registry(prompts_dir)

    # Get tool registry
    if tool_registry is None:
        tool_registry = get_default_registry()

    # Create the ProfileAgent
    profile_agent: ProfileAgent[PretranslationPhaseInput, IdiomAnnotationList] = (
        ProfileAgent(
            profile=profile,
            output_type=IdiomAnnotationList,
            layer_registry=layer_registry,
            tool_registry=tool_registry,
            config=config,
        )
    )

    # Wrap in PretranslationIdiomLabelerAgent
    return PretranslationIdiomLabelerAgent(
        profile_agent=profile_agent,
        config=config,
        chunk_size=chunk_size,
        source_lang=source_lang,
        target_lang=target_lang,
    )


class TranslateDirectTranslatorAgent:
    """Translate phase agent that produces translations using a ProfileAgent.

    This agent:
    1. Chunks source lines into batches for processing
    2. Formats context (scene summaries, inline pretranslation annotations)
    3. Runs ProfileAgent for each chunk to produce TranslationResultList
    4. Converts results to TranslatedLine and merges into TranslatePhaseOutput
    """

    def __init__(
        self,
        profile_agent: ProfileAgent[TranslatePhaseInput, TranslationResultList],
        config: ProfileAgentConfig,
        chunk_size: int = 10,
        source_lang: LanguageCode = "ja",
        target_lang: LanguageCode = "en",
    ) -> None:
        """Initialize the translate direct translator agent.

        Args:
            profile_agent: Underlying ProfileAgent for translation.
            config: Runtime configuration.
            chunk_size: Number of lines per processing chunk.
            source_lang: Source language name for prompts.
            target_lang: Target language name for prompts.
        """
        self._profile_agent = profile_agent
        self._config = config
        self._chunk_size = chunk_size
        self._source_lang = source_lang
        self._target_lang = target_lang

    async def run(self, payload: TranslatePhaseInput) -> TranslatePhaseOutput:
        """Execute translate phase by translating lines in chunks.

        Args:
            payload: Translate phase input with source lines.

        Returns:
            Translate phase output with translated lines.
        """
        from rentl_agents.translate.lines import (
            chunk_lines,
            format_annotated_lines_for_prompt,
            get_scene_summary_for_lines,
            merge_translated_lines,
            translation_result_to_lines,
        )

        # Chunk lines for batch processing
        chunks = chunk_lines(payload.source_lines, self._chunk_size)

        # Process each chunk
        all_translated_lines: list[TranslatedLine] = []
        for chunk in chunks:
            # Format lines with inline annotations and context for prompt
            annotated_lines_text = format_annotated_lines_for_prompt(
                chunk, payload.pretranslation_annotations
            )
            scene_summary_text = get_scene_summary_for_lines(
                chunk, payload.scene_summaries
            )

            # Update template context for this chunk
            context = TemplateContext(
                root_variables={},
                phase_variables={
                    "source_lang": self._source_lang,
                    "target_lang": self._target_lang,
                },
                agent_variables={
                    "annotated_source_lines": annotated_lines_text,
                    "scene_summary": scene_summary_text,
                    "line_count": str(len(chunk)),
                },
            )
            self._profile_agent.update_context(context)

            # Run the profile agent for this chunk
            # ProfileAgent returns TranslationResultList with translated lines
            result = await self._profile_agent.run(payload)
            translated_lines = translation_result_to_lines(result, chunk)
            all_translated_lines.extend(translated_lines)

        return merge_translated_lines(
            payload.run_id,
            payload.target_language,
            all_translated_lines,
        )


def create_translate_agent_from_profile(
    profile_path: Path,
    prompts_dir: Path,
    config: ProfileAgentConfig,
    tool_registry: ToolRegistry | None = None,
    chunk_size: int = 10,
    source_lang: LanguageCode = "ja",
    target_lang: LanguageCode = "en",
) -> TranslateDirectTranslatorAgent:
    """Create a translate phase agent from a TOML profile.

    Args:
        profile_path: Path to the agent profile TOML file.
        prompts_dir: Path to the prompts directory (containing root.toml, phases/).
        config: Runtime configuration (API key, model settings, etc.).
        tool_registry: Tool registry to use. Defaults to the default registry.
        chunk_size: Number of lines per processing chunk.
        source_lang: Source language name for prompts.
        target_lang: Target language name for prompts.

    Returns:
        Translate phase agent ready for orchestrator.

    Raises:
        ValueError: If profile is not for translate phase.
    """
    # Load the profile
    profile = load_agent_profile(profile_path)

    # Verify it's a translate phase agent
    if profile.meta.phase != PhaseName.TRANSLATE:
        raise ValueError(
            f"Profile {profile.meta.name} is for phase {profile.meta.phase.value}, "
            f"expected translate"
        )

    # Load prompt layers
    layer_registry = load_layer_registry(prompts_dir)

    # Get tool registry
    if tool_registry is None:
        tool_registry = get_default_registry()

    # Create the ProfileAgent
    profile_agent: ProfileAgent[TranslatePhaseInput, TranslationResultList] = (
        ProfileAgent(
            profile=profile,
            output_type=TranslationResultList,
            layer_registry=layer_registry,
            tool_registry=tool_registry,
            config=config,
        )
    )

    # Wrap in TranslateDirectTranslatorAgent
    return TranslateDirectTranslatorAgent(
        profile_agent=profile_agent,
        config=config,
        chunk_size=chunk_size,
        source_lang=source_lang,
        target_lang=target_lang,
    )


class QaStyleGuideCriticAgent:
    """QA phase agent that evaluates translations against style guide.

    This agent:
    1. Checks if a style guide is provided (returns empty if not)
    2. Chunks source and translated lines into batches for processing
    3. Runs ProfileAgent for each chunk to identify style violations
    4. Converts violations to QaIssue and merges into QaPhaseOutput
    """

    def __init__(
        self,
        profile_agent: ProfileAgent[QaPhaseInput, StyleGuideViolationList],
        config: ProfileAgentConfig,
        chunk_size: int = 10,
        source_lang: LanguageCode = "ja",
        target_lang: LanguageCode = "en",
        severity: QaSeverity = QaSeverity.MAJOR,
    ) -> None:
        """Initialize the QA style guide critic agent.

        Args:
            profile_agent: Underlying ProfileAgent for style guide evaluation.
            config: Runtime configuration.
            chunk_size: Number of lines per processing chunk.
            source_lang: Source language name for prompts.
            target_lang: Target language name for prompts.
            severity: Severity level for style violations.
        """
        self._profile_agent = profile_agent
        self._config = config
        self._chunk_size = chunk_size
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._severity = severity

    async def run(self, payload: QaPhaseInput) -> QaPhaseOutput:
        """Execute QA phase by evaluating translations against style guide.

        Args:
            payload: QA phase input with source lines, translations, and style guide.

        Returns:
            QA phase output with style guide violations as issues.
        """
        from rentl_agents.qa.lines import (
            chunk_qa_lines,
            empty_qa_output,
            format_lines_for_qa_prompt,
            merge_qa_agent_outputs,
            violation_to_qa_issue,
        )

        # Return empty output if no style guide provided
        if not payload.style_guide or not payload.style_guide.strip():
            return empty_qa_output(payload.run_id, payload.target_language)

        # Chunk lines for batch processing
        chunks = chunk_qa_lines(
            payload.source_lines,
            payload.translated_lines,
            self._chunk_size,
        )

        # Process each chunk
        all_issues: list[QaIssue] = []
        for source_chunk, translated_chunk in chunks:
            # Format lines for prompt
            lines_to_review = format_lines_for_qa_prompt(source_chunk, translated_chunk)

            # Update template context for this chunk
            context = TemplateContext(
                root_variables={},
                phase_variables={
                    "source_lang": self._source_lang,
                    "target_lang": self._target_lang,
                },
                agent_variables={
                    "style_guide": payload.style_guide,
                    "lines_to_review": lines_to_review,
                },
            )
            self._profile_agent.update_context(context)

            # Run the profile agent for this chunk
            # ProfileAgent returns StyleGuideViolationList with all violations found
            result = await self._profile_agent.run(payload)
            # Convert violations to QaIssue
            for violation in result.violations:
                issue = violation_to_qa_issue(violation, self._severity)
                all_issues.append(issue)

        return merge_qa_agent_outputs(
            payload.run_id,
            all_issues,
            payload.target_language,
        )


def create_qa_agent_from_profile(
    profile_path: Path,
    prompts_dir: Path,
    config: ProfileAgentConfig,
    tool_registry: ToolRegistry | None = None,
    chunk_size: int = 10,
    source_lang: LanguageCode = "ja",
    target_lang: LanguageCode = "en",
    severity: QaSeverity = QaSeverity.MAJOR,
) -> QaStyleGuideCriticAgent:
    """Create a QA phase agent from a TOML profile.

    Args:
        profile_path: Path to the agent profile TOML file.
        prompts_dir: Path to the prompts directory (containing root.toml, phases/).
        config: Runtime configuration (API key, model settings, etc.).
        tool_registry: Tool registry to use. Defaults to the default registry.
        chunk_size: Number of lines per processing chunk.
        source_lang: Source language name for prompts.
        target_lang: Target language name for prompts.
        severity: Severity level for style violations.

    Returns:
        QA phase agent ready for orchestrator.

    Raises:
        ValueError: If profile is not for QA phase.
    """
    # Load the profile
    profile = load_agent_profile(profile_path)

    # Verify it's a QA phase agent
    if profile.meta.phase != PhaseName.QA:
        raise ValueError(
            f"Profile {profile.meta.name} is for phase {profile.meta.phase.value}, "
            f"expected qa"
        )

    # Load prompt layers
    layer_registry = load_layer_registry(prompts_dir)

    # Get tool registry
    if tool_registry is None:
        tool_registry = get_default_registry()

    # Create the ProfileAgent
    profile_agent: ProfileAgent[QaPhaseInput, StyleGuideViolationList] = ProfileAgent(
        profile=profile,
        output_type=StyleGuideViolationList,
        layer_registry=layer_registry,
        tool_registry=tool_registry,
        config=config,
    )

    # Wrap in QaStyleGuideCriticAgent
    return QaStyleGuideCriticAgent(
        profile_agent=profile_agent,
        config=config,
        chunk_size=chunk_size,
        source_lang=source_lang,
        target_lang=target_lang,
        severity=severity,
    )


class EditBasicEditorAgent:
    """Edit phase agent that applies targeted edits with a ProfileAgent."""

    def __init__(
        self,
        profile_agent: ProfileAgent[EditPhaseInput, TranslationResultLine],
        config: ProfileAgentConfig,
        source_lang: LanguageCode = "ja",
        target_lang: LanguageCode = "en",
    ) -> None:
        """Initialize the edit agent.

        Args:
            profile_agent: Underlying ProfileAgent for editing.
            config: Runtime configuration.
            source_lang: Source language name for prompts.
            target_lang: Target language name for prompts.
        """
        self._profile_agent = profile_agent
        self._config = config
        self._source_lang = source_lang
        self._target_lang = target_lang

    async def run(self, payload: EditPhaseInput) -> EditPhaseOutput:
        """Execute edit phase by applying fixes to each translated line.

        Args:
            payload: Edit phase input with translated lines and QA issues.

        Returns:
            Edit phase output with edited lines and change log.
        """
        edited_lines: list[TranslatedLine] = []
        change_log: list[LineEdit] = []

        for line in payload.translated_lines:
            qa_text = self._format_qa_issues(payload.qa_issues, line.line_id)
            scene_summary = self._find_scene_summary(
                payload.scene_summaries, line.scene_id
            )

            context = TemplateContext(
                root_variables={},
                phase_variables={
                    "source_lang": self._source_lang,
                    "target_lang": self._target_lang,
                },
                agent_variables={
                    "line_id": line.line_id,
                    "source_text": line.source_text or "N/A",
                    "translated_text": line.text,
                    "qa_issues": qa_text,
                    "scene_summary": scene_summary,
                },
            )
            self._profile_agent.update_context(context)

            result = await self._profile_agent.run(payload)
            edited_text = result.text

            edited_lines.append(
                TranslatedLine(
                    line_id=line.line_id,
                    route_id=line.route_id,
                    scene_id=line.scene_id,
                    speaker=line.speaker,
                    source_text=line.source_text,
                    text=edited_text,
                    metadata=line.metadata,
                    source_columns=line.source_columns,
                )
            )

            if edited_text != line.text:
                change_log.append(
                    LineEdit(
                        line_id=line.line_id,
                        original_text=line.text,
                        edited_text=edited_text,
                        reason=self._edit_reason(payload.qa_issues, line.line_id),
                    )
                )

        return EditPhaseOutput(
            run_id=payload.run_id,
            phase=PhaseName.EDIT,
            target_language=payload.target_language,
            edited_lines=edited_lines,
            change_log=change_log,
        )

    @staticmethod
    def _format_qa_issues(issues: list[QaIssue] | None, line_id: str) -> str:
        if not issues:
            return "None"
        matches = [issue for issue in issues if issue.line_id == line_id]
        if not matches:
            return "None"
        formatted = []
        for issue in matches:
            severity = (
                issue.severity.value
                if hasattr(issue.severity, "value")
                else str(issue.severity)
            )
            category = (
                issue.category.value
                if hasattr(issue.category, "value")
                else str(issue.category)
            )
            formatted.append(f"- [{severity}/{category}] {issue.message}")
        return "\n".join(formatted)

    @staticmethod
    def _edit_reason(issues: list[QaIssue] | None, line_id: str) -> str | None:
        if not issues:
            return None
        matches = [issue for issue in issues if issue.line_id == line_id]
        if not matches:
            return None
        return "; ".join(issue.message for issue in matches)

    @staticmethod
    def _find_scene_summary(
        summaries: list[SceneSummary] | None, scene_id: str | None
    ) -> str:
        if not summaries or not scene_id:
            return "None"
        for summary in summaries:
            if summary.scene_id == scene_id:
                return summary.summary
        return "None"


def create_edit_agent_from_profile(
    profile_path: Path,
    prompts_dir: Path,
    config: ProfileAgentConfig,
    tool_registry: ToolRegistry | None = None,
    source_lang: LanguageCode = "ja",
    target_lang: LanguageCode = "en",
) -> EditBasicEditorAgent:
    """Create an edit phase agent from a TOML profile.

    Args:
        profile_path: Path to the agent profile TOML file.
        prompts_dir: Path to the prompts directory (containing root.toml, phases/).
        config: Runtime configuration (API key, model settings, etc.).
        tool_registry: Tool registry to use. Defaults to the default registry.
        source_lang: Source language name for prompts.
        target_lang: Target language name for prompts.

    Returns:
        Edit phase agent ready for orchestrator.

    Raises:
        ValueError: If profile is not for edit phase.
    """
    profile = load_agent_profile(profile_path)

    if profile.meta.phase != PhaseName.EDIT:
        raise ValueError(
            f"Profile {profile.meta.name} is for phase {profile.meta.phase.value}, "
            f"expected edit"
        )

    layer_registry = load_layer_registry(prompts_dir)

    if tool_registry is None:
        tool_registry = get_default_registry()

    profile_agent: ProfileAgent[EditPhaseInput, TranslationResultLine] = ProfileAgent(
        profile=profile,
        output_type=TranslationResultLine,
        layer_registry=layer_registry,
        tool_registry=tool_registry,
        config=config,
    )

    return EditBasicEditorAgent(
        profile_agent=profile_agent,
        config=config,
        source_lang=source_lang,
        target_lang=target_lang,
    )
