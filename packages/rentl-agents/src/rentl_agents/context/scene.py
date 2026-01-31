"""Scene validation and utilities for context phase.

This module provides:
- Scene validation for the scene summarizer
- Scene grouping utilities for sharding
- Output merging for context phase results
"""

from __future__ import annotations

from collections import defaultdict

from rentl_schemas.io import SourceLine
from rentl_schemas.phases import ContextPhaseOutput, SceneSummary
from rentl_schemas.primitives import RunId, SceneId


class SceneValidationError(Exception):
    """Raised when scene validation fails.

    Attributes:
        missing_count: Number of lines missing scene_id.
        line_ids: Sample of line IDs missing scene_id.
    """

    def __init__(
        self,
        message: str,
        missing_count: int,
        line_ids: list[str],
    ) -> None:
        """Initialize the scene validation error.

        Args:
            message: Error message.
            missing_count: Count of lines missing scene_id.
            line_ids: Sample of affected line IDs.
        """
        super().__init__(message)
        self.missing_count = missing_count
        self.line_ids = line_ids


def validate_scene_input(source_lines: list[SourceLine]) -> None:
    """Validate that all source lines have scene_id assigned.

    The scene summarizer requires scene_id on all lines. This validation
    should be called before processing to fail fast with a clear error.

    Args:
        source_lines: Source lines to validate.

    Raises:
        SceneValidationError: If any lines are missing scene_id.
    """
    missing = [line.line_id for line in source_lines if line.scene_id is None]

    if missing:
        sample = missing[:5]  # Show first 5 as example
        sample_str = ", ".join(sample)
        raise SceneValidationError(
            f"Scene Summarizer requires scene_id on all source lines. "
            f"{len(missing)} lines missing scene_id (examples: {sample_str}). "
            f"Use BatchSummarizer (v0.2+) for content without scene boundaries.",
            missing_count=len(missing),
            line_ids=missing,
        )


def group_lines_by_scene(
    source_lines: list[SourceLine],
) -> dict[SceneId, list[SourceLine]]:
    """Group source lines by scene_id.

    Args:
        source_lines: Source lines with scene_id assigned.

    Returns:
        Dictionary mapping scene_id to list of lines in that scene.
    """
    scenes: dict[SceneId, list[SourceLine]] = defaultdict(list)

    for line in source_lines:
        if line.scene_id is not None:
            scenes[line.scene_id].append(line)

    return dict(scenes)


def format_scene_lines(lines: list[SourceLine]) -> str:
    """Format scene lines for prompt injection.

    Creates a readable text block with speaker and dialogue.

    Args:
        lines: Source lines from a scene.

    Returns:
        Formatted string for prompt template.
    """
    formatted_lines: list[str] = []

    for line in lines:
        if line.speaker:
            formatted_lines.append(f"[{line.speaker}]: {line.text}")
        else:
            formatted_lines.append(line.text)

    return "\n".join(formatted_lines)


def merge_scene_summaries(
    run_id: RunId,
    summaries: list[SceneSummary],
) -> ContextPhaseOutput:
    """Merge scene summaries into a context phase output.

    Args:
        run_id: Run identifier.
        summaries: List of scene summaries from all scenes.

    Returns:
        Complete context phase output.
    """
    return ContextPhaseOutput(
        run_id=run_id,
        scene_summaries=summaries,
        context_notes=[],  # Scene summarizer doesn't produce context notes
        project_context=None,
        style_guide=None,
        glossary=None,
    )
