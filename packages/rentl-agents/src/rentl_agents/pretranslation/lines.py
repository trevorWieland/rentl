"""Line utilities for pretranslation phase.

This module provides:
- Line chunking for batch processing
- Line formatting for prompt injection
- Scene summary lookup for context
- Annotation conversion and merging
"""

from __future__ import annotations

from uuid import uuid7

from rentl_schemas.io import SourceLine
from rentl_schemas.phases import (
    IdiomAnnotation,
    PretranslationAnnotation,
    PretranslationPhaseOutput,
    SceneSummary,
)
from rentl_schemas.primitives import RunId, SceneId


def chunk_lines(
    source_lines: list[SourceLine],
    chunk_size: int = 10,
) -> list[list[SourceLine]]:
    """Split source lines into chunks for batch processing.

    Args:
        source_lines: Source lines to chunk.
        chunk_size: Maximum lines per chunk (default 50).

    Returns:
        List of line chunks, each containing up to chunk_size lines.

    Raises:
        ValueError: If chunk_size is not positive.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    chunks: list[list[SourceLine]] = []
    for i in range(0, len(source_lines), chunk_size):
        chunks.append(source_lines[i : i + chunk_size])

    return chunks


def format_lines_for_prompt(lines: list[SourceLine]) -> str:
    """Format source lines for prompt injection.

    Creates a readable text block with line IDs and speaker info.

    Args:
        lines: Source lines to format.

    Returns:
        Formatted string for prompt template.
    """
    formatted_lines: list[str] = []

    for line in lines:
        if line.speaker:
            formatted_lines.append(f"[{line.line_id}] [{line.speaker}]: {line.text}")
        else:
            formatted_lines.append(f"[{line.line_id}]: {line.text}")

    return "\n".join(formatted_lines)


def get_scene_summary_for_lines(
    lines: list[SourceLine],
    scene_summaries: list[SceneSummary] | None,
) -> str:
    """Get relevant scene summaries for a set of lines.

    Looks up scene summaries for all unique scene IDs in the lines.

    Args:
        lines: Source lines with optional scene_id.
        scene_summaries: Available scene summaries from context phase.

    Returns:
        Combined scene summary text, or empty string if none available.
    """
    if not scene_summaries:
        return ""

    # Get unique scene IDs from lines
    scene_ids: set[SceneId] = {
        line.scene_id for line in lines if line.scene_id is not None
    }

    if not scene_ids:
        return ""

    # Build scene ID to summary mapping
    summary_map: dict[SceneId, SceneSummary] = {
        summary.scene_id: summary for summary in scene_summaries
    }

    # Collect summaries for our scenes
    relevant_summaries: list[str] = []
    for scene_id in sorted(scene_ids):
        if scene_id in summary_map:
            summary = summary_map[scene_id]
            relevant_summaries.append(f"[{scene_id}]: {summary.summary}")

    return "\n".join(relevant_summaries)


def idiom_to_annotation(idiom: IdiomAnnotation) -> PretranslationAnnotation:
    """Convert an IdiomAnnotation to a PretranslationAnnotation.

    Creates a standardized annotation with the idiom details stored
    in the metadata field.

    Args:
        idiom: Idiom annotation from the idiom labeler.

    Returns:
        PretranslationAnnotation with annotation_type="idiom".
    """
    return PretranslationAnnotation(
        annotation_id=uuid7(),
        line_id=idiom.line_id,
        annotation_type="idiom",
        value=idiom.idiom_text,
        notes=idiom.explanation,
        metadata={
            "idiom_type": idiom.idiom_type,
            "translation_hint": idiom.translation_hint,
        },
    )


def merge_idiom_annotations(
    run_id: RunId,
    idiom_annotations: list[IdiomAnnotation],
) -> PretranslationPhaseOutput:
    """Merge idiom annotations into a pretranslation phase output.

    Converts all IdiomAnnotation records to PretranslationAnnotation
    and packages them in a phase output.

    Args:
        run_id: Run identifier.
        idiom_annotations: List of idiom annotations from all chunks.

    Returns:
        Complete pretranslation phase output.
    """
    annotations = [idiom_to_annotation(idiom) for idiom in idiom_annotations]

    return PretranslationPhaseOutput(
        run_id=run_id,
        annotations=annotations,
        term_candidates=[],  # Idiom labeler doesn't produce term candidates
    )
