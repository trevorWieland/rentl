"""Profile agent factory for creating orchestrator-ready agents.

This module provides factory functions to create phase agents from TOML profiles
and wire them to the pipeline orchestrator.
"""

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from rentl_agents.context.scene import (
    format_scene_lines,
    group_lines_by_scene,
    validate_scene_input,
)
from rentl_agents.layers import load_layer_registry
from rentl_agents.pretranslation.lines import (
    chunk_lines as chunk_pretranslation_lines,
)
from rentl_agents.pretranslation.lines import (
    format_lines_for_prompt,
    merge_idiom_annotations,
)
from rentl_agents.pretranslation.lines import (
    get_scene_summary_for_lines as get_scene_summary_for_pretranslation_lines,
)
from rentl_agents.profiles.loader import load_agent_profile
from rentl_agents.qa.lines import (
    chunk_qa_lines,
    empty_qa_output,
    format_lines_for_qa_prompt,
    merge_qa_agent_outputs,
    violation_to_qa_issue,
)
from rentl_agents.runtime import ProfileAgent, ProfileAgentConfig
from rentl_agents.templates import TemplateContext
from rentl_agents.tools.registry import ToolRegistry, get_default_registry
from rentl_agents.translate.lines import (
    chunk_lines as chunk_translate_lines,
)
from rentl_agents.translate.lines import (
    format_annotated_lines_for_prompt,
    merge_translated_lines,
    translation_result_to_lines,
)
from rentl_agents.translate.lines import (
    get_scene_summary_for_lines as get_scene_summary_for_translate_lines,
)
from rentl_core import AgentTelemetryEmitter
from rentl_core.orchestrator import PhaseAgentPool
from rentl_core.ports.orchestrator import (
    ContextAgentPoolProtocol,
    EditAgentPoolProtocol,
    PhaseAgentPoolProtocol,
    PretranslationAgentPoolProtocol,
    QaAgentPoolProtocol,
    TranslateAgentPoolProtocol,
)
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.config import (
    ModelEndpointConfig,
    ModelSettings,
    PhaseConfig,
    PhaseExecutionConfig,
    RetryConfig,
    RunConfig,
)
from rentl_schemas.io import TranslatedLine
from rentl_schemas.phases import (
    ContextPhaseInput,
    ContextPhaseOutput,
    EditPhaseInput,
    EditPhaseOutput,
    IdiomAnnotationList,
    IdiomReviewLine,
    PretranslationPhaseInput,
    PretranslationPhaseOutput,
    QaPhaseInput,
    QaPhaseOutput,
    SceneSummary,
    StyleGuideReviewList,
    TranslatePhaseInput,
    TranslatePhaseOutput,
    TranslationResultLine,
    TranslationResultList,
)
from rentl_schemas.primitives import LanguageCode, PhaseName, QaSeverity
from rentl_schemas.qa import LineEdit, QaIssue

if TYPE_CHECKING:
    pass


def _format_id_list(values: list[str], limit: int = 5) -> str:
    if not values:
        return "none"
    preview = values[:limit]
    suffix = "" if len(values) <= limit else f" (+{len(values) - limit} more)"
    return ", ".join(preview) + suffix


def _alignment_feedback(
    *,
    expected_ids: list[str],
    actual_ids: list[str],
    label: str,
) -> str | None:
    expected_set = set(expected_ids)
    actual_set = set(actual_ids)

    missing = [line_id for line_id in expected_ids if line_id not in actual_set]
    extra = [line_id for line_id in actual_ids if line_id not in expected_set]

    duplicates = [
        line_id for line_id, count in Counter(actual_ids).items() if count > 1
    ]

    if (
        not missing
        and not extra
        and not duplicates
        and len(expected_ids) == len(actual_ids)
    ):
        return None

    parts = [
        "Alignment error: output IDs must exactly match input IDs.",
        f"Expected {len(expected_ids)} {label} ID(s), got {len(actual_ids)}.",
    ]
    if missing:
        parts.append(f"Missing: {_format_id_list(missing)}")
    if extra:
        parts.append(f"Extra: {_format_id_list(extra)}")
    if duplicates:
        parts.append(f"Duplicate: {_format_id_list(duplicates)}")
    parts.append("Return EXACTLY one output per input ID with no extras or omissions.")
    return " ".join(parts)


def _max_chunk_attempts(config: ProfileAgentConfig) -> int:
    retries = max(config.max_output_retries, 0)
    return retries + 1


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

        Raises:
            RuntimeError: If the scene_id in output does not match the input
                after retries.
        """
        # Validate all lines have scene_id
        validate_scene_input(payload.source_lines)

        # Group lines by scene
        scene_groups = group_lines_by_scene(payload.source_lines)

        # Summarize each scene
        summaries: list[SceneSummary] = []
        for scene_id, lines in scene_groups.items():
            max_attempts = _max_chunk_attempts(self._config)
            alignment_feedback = "None"
            for attempt in range(1, max_attempts + 1):
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
                        "alignment_feedback": alignment_feedback,
                    },
                )
                self._profile_agent.update_context(context)

                # Run the profile agent for this scene
                # Note: ProfileAgent returns SceneSummary directly
                summary = await self._profile_agent.run(payload)
                if summary.scene_id != scene_id:
                    alignment_feedback = (
                        "Alignment error: scene_id must match the input scene. "
                        f"Expected {scene_id}, got {summary.scene_id}. "
                        "Return the exact input scene_id with no changes."
                    )
                    if attempt == max_attempts:
                        raise RuntimeError(alignment_feedback)
                    continue
                summaries.append(summary)
                break

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
    telemetry_emitter: AgentTelemetryEmitter | None = None,
) -> ContextSceneSummarizerAgent:
    """Create a context phase agent from a TOML profile.

    Args:
        profile_path: Path to the agent profile TOML file.
        prompts_dir: Path to the prompts directory (containing root.toml, phases/).
        config: Runtime configuration (API key, model settings, etc.).
        tool_registry: Tool registry to use. Defaults to the default registry.
        source_lang: Source language name for prompts.
        target_lang: Target language name for prompts.
        telemetry_emitter: Optional telemetry emitter for agent status.

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

    runtime_config = _with_required_tools_from_profile(config, profile)

    # Create the ProfileAgent
    profile_agent: ProfileAgent[ContextPhaseInput, SceneSummary] = ProfileAgent(
        profile=profile,
        output_type=SceneSummary,
        layer_registry=layer_registry,
        tool_registry=tool_registry,
        config=runtime_config,
        telemetry_emitter=telemetry_emitter,
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
    # File is in: site-packages/rentl_agents/wiring.py (when installed)
    # Prompts are in: site-packages/rentl_agents/prompts/
    return Path(__file__).parent / "prompts"


def get_default_agents_dir() -> Path:
    """Get the default agents directory path.

    Returns:
        Path to the agents directory in rentl-agents package.
    """
    # File is in: site-packages/rentl_agents/wiring.py (when installed)
    # Agents are in: site-packages/rentl_agents/agents/
    return Path(__file__).parent / "agents"


def _with_required_tools_from_profile(
    config: ProfileAgentConfig,
    profile: AgentProfileConfig,
) -> ProfileAgentConfig:
    required_tools = profile.tools.required
    if not required_tools:
        return config
    return config.model_copy(update={"required_tool_calls": list(required_tools)})


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

        Raises:
            RuntimeError: If idiom line_ids do not align with input lines after retries.
        """
        # Chunk lines for batch processing
        chunks = chunk_pretranslation_lines(payload.source_lines, self._chunk_size)

        # Process each chunk
        all_reviews: list[IdiomReviewLine] = []
        max_attempts = _max_chunk_attempts(self._config)
        for chunk in chunks:
            expected_ids = [line.line_id for line in chunk]
            alignment_feedback = "None"
            for attempt in range(1, max_attempts + 1):
                # Format lines for prompt
                source_lines_text = format_lines_for_prompt(chunk)
                scene_summary_text = get_scene_summary_for_pretranslation_lines(
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
                        "alignment_feedback": alignment_feedback,
                    },
                )
                self._profile_agent.update_context(context)

                # Run the profile agent for this chunk
                # ProfileAgent returns IdiomAnnotationList with per-line reviews
                result = await self._profile_agent.run(payload)
                actual_ids = [review.line_id for review in result.reviews]
                feedback = _alignment_feedback(
                    expected_ids=expected_ids,
                    actual_ids=actual_ids,
                    label="line",
                )
                if feedback is not None:
                    alignment_feedback = feedback
                    if attempt == max_attempts:
                        raise RuntimeError(alignment_feedback)
                    continue
                all_reviews.extend(result.reviews)
                break

        return merge_idiom_annotations(payload.run_id, all_reviews)


def create_pretranslation_agent_from_profile(
    profile_path: Path,
    prompts_dir: Path,
    config: ProfileAgentConfig,
    tool_registry: ToolRegistry | None = None,
    chunk_size: int = 10,
    source_lang: LanguageCode = "ja",
    target_lang: LanguageCode = "en",
    telemetry_emitter: AgentTelemetryEmitter | None = None,
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
        telemetry_emitter: Optional telemetry emitter for agent status.

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

    runtime_config = _with_required_tools_from_profile(config, profile)

    # Create the ProfileAgent
    profile_agent: ProfileAgent[PretranslationPhaseInput, IdiomAnnotationList] = (
        ProfileAgent(
            profile=profile,
            output_type=IdiomAnnotationList,
            layer_registry=layer_registry,
            tool_registry=tool_registry,
            config=runtime_config,
            telemetry_emitter=telemetry_emitter,
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

        Raises:
            RuntimeError: If translated line_ids do not align with input lines
                after retries.
        """
        # Chunk lines for batch processing
        chunks = chunk_translate_lines(payload.source_lines, self._chunk_size)

        # Process each chunk
        all_translated_lines: list[TranslatedLine] = []
        max_attempts = _max_chunk_attempts(self._config)
        for chunk in chunks:
            expected_ids = [line.line_id for line in chunk]
            alignment_feedback = "None"
            for attempt in range(1, max_attempts + 1):
                # Format lines with inline annotations and context for prompt
                annotated_lines_text = format_annotated_lines_for_prompt(
                    chunk, payload.pretranslation_annotations
                )
                scene_summary_text = get_scene_summary_for_translate_lines(
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
                        "alignment_feedback": alignment_feedback,
                    },
                )
                self._profile_agent.update_context(context)

                # Run the profile agent for this chunk
                # ProfileAgent returns TranslationResultList with translated lines
                result = await self._profile_agent.run(payload)
                actual_ids = [
                    translation.line_id for translation in result.translations
                ]
                feedback = _alignment_feedback(
                    expected_ids=expected_ids,
                    actual_ids=actual_ids,
                    label="line",
                )
                if feedback is not None:
                    alignment_feedback = feedback
                    if attempt == max_attempts:
                        raise RuntimeError(alignment_feedback)
                    continue
                translated_lines = translation_result_to_lines(result, chunk)
                all_translated_lines.extend(translated_lines)
                break

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
    telemetry_emitter: AgentTelemetryEmitter | None = None,
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
        telemetry_emitter: Optional telemetry emitter for agent status.

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

    runtime_config = _with_required_tools_from_profile(config, profile)

    # Create the ProfileAgent
    profile_agent: ProfileAgent[TranslatePhaseInput, TranslationResultList] = (
        ProfileAgent(
            profile=profile,
            output_type=TranslationResultList,
            layer_registry=layer_registry,
            tool_registry=tool_registry,
            config=runtime_config,
            telemetry_emitter=telemetry_emitter,
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
        profile_agent: ProfileAgent[QaPhaseInput, StyleGuideReviewList],
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

        Raises:
            RuntimeError: If QA reviews do not align with input lines after retries.
        """
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
        max_attempts = _max_chunk_attempts(self._config)
        for source_chunk, translated_chunk in chunks:
            expected_ids = [line.line_id for line in source_chunk]
            alignment_feedback = "None"
            for attempt in range(1, max_attempts + 1):
                # Format lines for prompt
                lines_to_review = format_lines_for_qa_prompt(
                    source_chunk, translated_chunk
                )

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
                        "alignment_feedback": alignment_feedback,
                    },
                )
                self._profile_agent.update_context(context)

                # Run the profile agent for this chunk
                # ProfileAgent returns StyleGuideReviewList with all reviews found
                result = await self._profile_agent.run(payload)
                actual_ids = [review.line_id for review in result.reviews]
                feedback = _alignment_feedback(
                    expected_ids=expected_ids,
                    actual_ids=actual_ids,
                    label="line",
                )
                if feedback is not None:
                    alignment_feedback = feedback
                    if attempt == max_attempts:
                        raise RuntimeError(alignment_feedback)
                    continue
                # Convert violations to QaIssue
                for review in result.reviews:
                    for violation in review.violations:
                        issue = violation_to_qa_issue(
                            violation,
                            self._severity,
                            line_id=review.line_id,
                        )
                        all_issues.append(issue)
                break

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
    telemetry_emitter: AgentTelemetryEmitter | None = None,
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
        telemetry_emitter: Optional telemetry emitter for agent status.

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

    runtime_config = _with_required_tools_from_profile(config, profile)

    # Create the ProfileAgent
    profile_agent: ProfileAgent[QaPhaseInput, StyleGuideReviewList] = ProfileAgent(
        profile=profile,
        output_type=StyleGuideReviewList,
        layer_registry=layer_registry,
        tool_registry=tool_registry,
        config=runtime_config,
        telemetry_emitter=telemetry_emitter,
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

        Raises:
            RuntimeError: If edited line_ids do not match input line_ids after retries.
        """
        edited_lines: list[TranslatedLine] = []
        change_log: list[LineEdit] = []
        max_attempts = _max_chunk_attempts(self._config)

        for line in payload.translated_lines:
            alignment_feedback = "None"
            for attempt in range(1, max_attempts + 1):
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
                        "alignment_feedback": alignment_feedback,
                    },
                )
                self._profile_agent.update_context(context)

                result = await self._profile_agent.run(payload)
                if result.line_id != line.line_id:
                    alignment_feedback = (
                        "Alignment error: line_id must match the input line. "
                        f"Expected {line.line_id}, got {result.line_id}. "
                        "Return the exact input line_id with no changes."
                    )
                    if attempt == max_attempts:
                        raise RuntimeError(alignment_feedback)
                    continue
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
                break

        # Aggregate validation: edited output must match input lines exactly
        input_ids = {line.line_id for line in payload.translated_lines}
        output_ids = {line.line_id for line in edited_lines}
        if len(edited_lines) != len(payload.translated_lines):
            raise RuntimeError(
                f"Edit output line count mismatch: "
                f"expected {len(payload.translated_lines)}, "
                f"got {len(edited_lines)}"
            )
        if output_ids != input_ids:
            missing = input_ids - output_ids
            extra = output_ids - input_ids
            parts = []
            if missing:
                parts.append(f"missing={sorted(missing)}")
            if extra:
                parts.append(f"extra={sorted(extra)}")
            raise RuntimeError(f"Edit output line ID mismatch: {', '.join(parts)}")

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
    telemetry_emitter: AgentTelemetryEmitter | None = None,
) -> EditBasicEditorAgent:
    """Create an edit phase agent from a TOML profile.

    Args:
        profile_path: Path to the agent profile TOML file.
        prompts_dir: Path to the prompts directory (containing root.toml, phases/).
        config: Runtime configuration (API key, model settings, etc.).
        tool_registry: Tool registry to use. Defaults to the default registry.
        source_lang: Source language name for prompts.
        target_lang: Target language name for prompts.
        telemetry_emitter: Optional telemetry emitter for agent status.

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

    runtime_config = _with_required_tools_from_profile(config, profile)

    profile_agent: ProfileAgent[EditPhaseInput, TranslationResultLine] = ProfileAgent(
        profile=profile,
        output_type=TranslationResultLine,
        layer_registry=layer_registry,
        tool_registry=tool_registry,
        config=runtime_config,
        telemetry_emitter=telemetry_emitter,
    )

    return EditBasicEditorAgent(
        profile_agent=profile_agent,
        config=config,
        source_lang=source_lang,
        target_lang=target_lang,
    )


class AgentPoolBundle(BaseModel):
    """Agent pools wired for pipeline execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    context_agents: list[tuple[str, ContextAgentPoolProtocol]]
    pretranslation_agents: list[tuple[str, PretranslationAgentPoolProtocol]]
    translate_agents: list[tuple[str, TranslateAgentPoolProtocol]]
    qa_agents: list[tuple[str, QaAgentPoolProtocol]]
    edit_agents: list[tuple[str, EditAgentPoolProtocol]]


class _AgentProfileSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    profile: AgentProfileConfig
    path: Path


def build_agent_pools(
    *,
    config: RunConfig,
    telemetry_emitter: AgentTelemetryEmitter | None = None,
    phases: Sequence[PhaseName] | None = None,
) -> AgentPoolBundle:
    """Build agent pools from run configuration.

    Args:
        config: Run configuration with agent profile paths.
        telemetry_emitter: Optional telemetry emitter for agent status.
        phases: Optional phase list to limit agent wiring.

    Returns:
        AgentPoolBundle: Configured agent pools.
    """
    if config.agents is None:
        prompts_dir = get_default_prompts_dir()
        agents_dir = get_default_agents_dir()
    else:
        agents_config = config.agents
        workspace_dir = Path(config.project.paths.workspace_dir)
        prompts_dir = resolve_agent_path(agents_config.prompts_dir, workspace_dir)
        agents_dir = resolve_agent_path(agents_config.agents_dir, workspace_dir)
    source_lang = config.project.languages.source_language
    target_lang = _resolve_primary_target_language(config)
    tool_registry = get_default_registry()
    profile_specs = _discover_agent_profile_specs(agents_dir)
    phases_to_load = (
        set(phases)
        if phases is not None
        else {phase.phase for phase in config.pipeline.phases if phase.enabled}
    )

    context_agents = _build_phase_agent_entries(
        PhaseName.CONTEXT,
        phases_to_load,
        config,
        profile_specs,
        prompts_dir,
        tool_registry,
        source_lang,
        target_lang,
        telemetry_emitter,
    )
    pretranslation_agents = _build_phase_agent_entries(
        PhaseName.PRETRANSLATION,
        phases_to_load,
        config,
        profile_specs,
        prompts_dir,
        tool_registry,
        source_lang,
        target_lang,
        telemetry_emitter,
    )
    translate_agents = _build_phase_agent_entries(
        PhaseName.TRANSLATE,
        phases_to_load,
        config,
        profile_specs,
        prompts_dir,
        tool_registry,
        source_lang,
        target_lang,
        telemetry_emitter,
    )
    qa_agents = _build_phase_agent_entries(
        PhaseName.QA,
        phases_to_load,
        config,
        profile_specs,
        prompts_dir,
        tool_registry,
        source_lang,
        target_lang,
        telemetry_emitter,
    )
    edit_agents = _build_phase_agent_entries(
        PhaseName.EDIT,
        phases_to_load,
        config,
        profile_specs,
        prompts_dir,
        tool_registry,
        source_lang,
        target_lang,
        telemetry_emitter,
    )

    return AgentPoolBundle(
        context_agents=context_agents,
        pretranslation_agents=pretranslation_agents,
        translate_agents=translate_agents,
        qa_agents=qa_agents,
        edit_agents=edit_agents,
    )


def resolve_agent_path(value: str, workspace_dir: Path) -> Path:
    """Resolve an agent path and enforce workspace containment.

    Returns:
        Resolved absolute path within the workspace.

    Raises:
        ValueError: If the resolved path escapes the workspace directory.
    """
    resolved_workspace = workspace_dir.resolve()
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (resolved_workspace / path).resolve()
    try:
        resolved.relative_to(resolved_workspace)
    except ValueError as exc:
        raise ValueError(
            f"Agent path escapes workspace: {value!r} resolves to "
            f"{resolved}, which is outside {resolved_workspace}"
        ) from exc
    return resolved


def _discover_agent_profile_specs(agents_dir: Path) -> dict[str, _AgentProfileSpec]:
    specs: dict[str, _AgentProfileSpec] = {}
    if not agents_dir.exists():
        return specs
    for phase in PhaseName:
        if phase in {PhaseName.INGEST, PhaseName.EXPORT}:
            continue
        phase_dir = agents_dir / phase.value
        if not phase_dir.exists():
            continue
        for toml_path in phase_dir.glob("*.toml"):
            profile = load_agent_profile(toml_path)
            if profile.meta.phase != phase:
                raise ValueError(
                    f"Agent {profile.meta.name} declares phase "
                    f"{profile.meta.phase.value} but is in {phase.value}/"
                )
            name = profile.meta.name
            if name in specs:
                raise ValueError(f"Duplicate agent name: {name}")
            specs[name] = _AgentProfileSpec(
                name=name,
                profile=profile,
                path=toml_path,
            )
    return specs


def _resolve_phase_agent_specs(
    config: RunConfig,
    specs: dict[str, _AgentProfileSpec],
    phase: PhaseName,
) -> list[_AgentProfileSpec]:
    phase_config = _resolve_phase_config(config, phase)
    if phase_config is None or not phase_config.enabled:
        return []
    if not phase_config.agents:
        raise ValueError(f"agents must be configured for {phase.value} phase")
    resolved: list[_AgentProfileSpec] = []
    for agent_name in phase_config.agents:
        spec = specs.get(agent_name)
        if spec is None:
            available = ", ".join(sorted(specs.keys())) or "none"
            raise ValueError(
                f"Unknown agent '{agent_name}' for phase {phase.value}. "
                f"Available: {available}"
            )
        if spec.profile.meta.phase != phase:
            raise ValueError(
                f"Agent {agent_name} is for phase {spec.profile.meta.phase.value} "
                f"but was configured for {phase.value}"
            )
        resolved.append(spec)
    return resolved


def _build_phase_agent_entries(
    phase: PhaseName,
    phases_to_load: set[PhaseName],
    config: RunConfig,
    profile_specs: dict[str, _AgentProfileSpec],
    prompts_dir: Path,
    tool_registry: ToolRegistry,
    source_lang: LanguageCode,
    target_lang: LanguageCode,
    telemetry_emitter: AgentTelemetryEmitter | None,
) -> list[tuple[str, PhaseAgentPoolProtocol]]:
    if phase not in phases_to_load:
        return []
    resolved = _resolve_phase_agent_specs(config, profile_specs, phase)
    if not resolved:
        return []
    execution = _resolve_phase_execution(config, phase)
    agent_config = _build_profile_agent_config(config, phase)

    entries: list[tuple[str, PhaseAgentPoolProtocol]] = []
    for spec in resolved:
        pool: PhaseAgentPoolProtocol
        if phase == PhaseName.CONTEXT:
            pool = PhaseAgentPool.from_factory(
                factory=lambda path=spec.path: create_context_agent_from_profile(
                    profile_path=path,
                    prompts_dir=prompts_dir,
                    config=agent_config,
                    tool_registry=tool_registry,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    telemetry_emitter=telemetry_emitter,
                ),
                count=_resolve_agent_pool_size(execution),
                max_parallel=_resolve_agent_pool_max_parallel(execution),
            )
        elif phase == PhaseName.PRETRANSLATION:
            pool = PhaseAgentPool.from_factory(
                factory=lambda path=spec.path: create_pretranslation_agent_from_profile(
                    profile_path=path,
                    prompts_dir=prompts_dir,
                    config=agent_config,
                    tool_registry=tool_registry,
                    chunk_size=_resolve_chunk_size(execution),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    telemetry_emitter=telemetry_emitter,
                ),
                count=_resolve_agent_pool_size(execution),
                max_parallel=_resolve_agent_pool_max_parallel(execution),
            )
        elif phase == PhaseName.TRANSLATE:
            pool = PhaseAgentPool.from_factory(
                factory=lambda path=spec.path: create_translate_agent_from_profile(
                    profile_path=path,
                    prompts_dir=prompts_dir,
                    config=agent_config,
                    tool_registry=tool_registry,
                    chunk_size=_resolve_chunk_size(execution),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    telemetry_emitter=telemetry_emitter,
                ),
                count=_resolve_agent_pool_size(execution),
                max_parallel=_resolve_agent_pool_max_parallel(execution),
            )
        elif phase == PhaseName.QA:
            pool = PhaseAgentPool.from_factory(
                factory=lambda path=spec.path: create_qa_agent_from_profile(
                    profile_path=path,
                    prompts_dir=prompts_dir,
                    config=agent_config,
                    tool_registry=tool_registry,
                    chunk_size=_resolve_chunk_size(execution),
                    source_lang=source_lang,
                    target_lang=target_lang,
                    telemetry_emitter=telemetry_emitter,
                ),
                count=_resolve_agent_pool_size(execution),
                max_parallel=_resolve_agent_pool_max_parallel(execution),
            )
        elif phase == PhaseName.EDIT:
            pool = PhaseAgentPool.from_factory(
                factory=lambda path=spec.path: create_edit_agent_from_profile(
                    profile_path=path,
                    prompts_dir=prompts_dir,
                    config=agent_config,
                    tool_registry=tool_registry,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    telemetry_emitter=telemetry_emitter,
                ),
                count=_resolve_agent_pool_size(execution),
                max_parallel=_resolve_agent_pool_max_parallel(execution),
            )
        else:
            raise ValueError(f"Unsupported phase: {phase.value}")
        entries.append((spec.name, pool))
    return entries


def _resolve_primary_target_language(config: RunConfig) -> LanguageCode:
    targets = config.project.languages.target_languages
    if not targets:
        raise ValueError("No target languages configured")
    return targets[0]


def _resolve_phase_execution(
    config: RunConfig, phase: PhaseName
) -> PhaseExecutionConfig | None:
    phase_config = _resolve_phase_config(config, phase)
    if phase_config is None:
        return None
    return phase_config.execution


def _resolve_chunk_size(execution: PhaseExecutionConfig | None) -> int:
    if execution and execution.chunk_size is not None:
        return execution.chunk_size
    return 10


def _resolve_agent_pool_size(execution: PhaseExecutionConfig | None) -> int:
    if execution and execution.max_parallel_agents is not None:
        return execution.max_parallel_agents
    return 1


def _resolve_agent_pool_max_parallel(
    execution: PhaseExecutionConfig | None,
) -> int | None:
    if execution and execution.max_parallel_agents is not None:
        return execution.max_parallel_agents
    return None


def _resolve_phase_config(config: RunConfig, phase: PhaseName) -> PhaseConfig | None:
    for entry in config.pipeline.phases:
        if entry.phase == phase:
            return entry
    return None


def _resolve_phase_model(config: RunConfig, phase: PhaseName) -> ModelSettings:
    phase_config = _resolve_phase_config(config, phase)
    if phase_config is not None and phase_config.model is not None:
        return phase_config.model
    if config.pipeline.default_model is None:
        raise ValueError("default_model is required for agent phases")
    return config.pipeline.default_model


def _resolve_phase_retry(config: RunConfig, phase: PhaseName) -> RetryConfig:
    phase_config = _resolve_phase_config(config, phase)
    if phase_config is not None and phase_config.retry is not None:
        return phase_config.retry
    return config.retry


def _resolve_endpoint_config(
    config: RunConfig, model_settings: ModelSettings
) -> ModelEndpointConfig:
    if config.endpoints is None:
        endpoint = config.endpoint
        if endpoint is None:
            raise ValueError("Endpoint configuration is required")
        return endpoint
    endpoint_ref = config.resolve_endpoint_ref(model=model_settings)
    if endpoint_ref is None:
        raise ValueError("Endpoint reference could not be resolved")
    for endpoint in config.endpoints.endpoints:
        if endpoint.provider_name == endpoint_ref:
            return endpoint
    raise ValueError(f"Unknown endpoint reference: {endpoint_ref}")


def _build_profile_agent_config(
    config: RunConfig, phase: PhaseName
) -> ProfileAgentConfig:
    model_settings = _resolve_phase_model(config, phase)
    endpoint = _resolve_endpoint_config(config, model_settings)
    api_key = os.getenv(endpoint.api_key_env)
    if api_key is None:
        raise ValueError(
            f"Missing API key environment variable: {endpoint.api_key_env}"
        )
    retry_config = _resolve_phase_retry(config, phase)

    return ProfileAgentConfig(
        api_key=api_key,
        base_url=endpoint.base_url,
        model_id=model_settings.model_id,
        temperature=model_settings.temperature,
        top_p=model_settings.top_p,
        timeout_s=endpoint.timeout_s,
        openrouter_provider=endpoint.openrouter_provider,
        max_output_tokens=model_settings.max_output_tokens,
        max_retries=retry_config.max_retries,
        retry_base_delay=retry_config.backoff_s,
    )
