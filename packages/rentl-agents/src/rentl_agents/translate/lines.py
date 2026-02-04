"""Line utilities for translate phase.

This module provides:
- Line chunking for batch processing
- Line formatting for prompt injection
- Scene summary lookup for context
- Pretranslation annotation formatting
- Glossary term formatting
- Translation result conversion and merging
"""

from __future__ import annotations

from collections import Counter

from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.phases import (
    GlossaryTerm,
    PretranslationAnnotation,
    SceneSummary,
    TranslatePhaseOutput,
    TranslationResultList,
)
from rentl_schemas.primitives import LanguageCode, LineId, RunId, SceneId


def chunk_lines(
    source_lines: list[SourceLine],
    chunk_size: int = 10,
) -> list[list[SourceLine]]:
    """Split source lines into scene-aware chunks for batch processing.

    This function respects scene boundaries when chunking:
    - Lines from the same scene stay together when possible
    - A scene that exceeds chunk_size is split at chunk_size boundaries
    - Small consecutive scenes are combined up to chunk_size

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

    if not source_lines:
        return []

    # Group lines by scene, preserving order
    scene_groups: list[list[SourceLine]] = []
    current_scene: SceneId | None = None
    current_group: list[SourceLine] = []

    for line in source_lines:
        scene_id = line.scene_id
        if scene_id != current_scene:
            if current_group:
                scene_groups.append(current_group)
            current_group = [line]
            current_scene = scene_id
        else:
            current_group.append(line)

    if current_group:
        scene_groups.append(current_group)

    # Build chunks from scene groups
    chunks: list[list[SourceLine]] = []
    current_chunk: list[SourceLine] = []

    for scene_group in scene_groups:
        # If scene group fits in remaining chunk space, add it
        if len(current_chunk) + len(scene_group) <= chunk_size:
            current_chunk.extend(scene_group)
        # If scene group is larger than chunk_size, split it
        elif len(scene_group) > chunk_size:
            # Flush current chunk if not empty
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
            # Split large scene into chunks
            for i in range(0, len(scene_group), chunk_size):
                chunks.append(scene_group[i : i + chunk_size])
        # Otherwise, start a new chunk with this scene group
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = list(scene_group)

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)

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
        formatted_lines.append(f"[{line.line_id}]")
        if line.speaker:
            formatted_lines.append(f"Speaker: {line.speaker}")
        formatted_lines.extend((f"Text: {line.text}", ""))

    return "\n".join(formatted_lines).strip()


def format_annotated_lines_for_prompt(
    lines: list[SourceLine],
    annotations: list[PretranslationAnnotation] | None,
) -> str:
    """Format source lines with inline pretranslation annotations.

    Creates a readable text block where each source line is followed by
    any relevant annotations for that line. This keeps annotations
    contextually close to the lines they describe.

    Args:
        lines: Source lines to format.
        annotations: Available pretranslation annotations.

    Returns:
        Formatted string for prompt template with inline annotations.
    """
    if not lines:
        return ""

    # Build annotation lookup by line_id
    annotation_map: dict[LineId, list[PretranslationAnnotation]] = {}
    if annotations:
        for ann in annotations:
            if ann.line_id not in annotation_map:
                annotation_map[ann.line_id] = []
            annotation_map[ann.line_id].append(ann)

    formatted_lines: list[str] = []

    for line in lines:
        # Format the source line
        formatted_lines.append(f"[{line.line_id}]")
        if line.speaker:
            formatted_lines.append(f"Speaker: {line.speaker}")
        formatted_lines.append(f"Text: {line.text}")

        # Add inline annotations for this line
        line_annotations = annotation_map.get(line.line_id, [])
        for ann in line_annotations:
            # Format annotation with type, value, notes, and optional hint
            parts: list[str] = []
            if ann.annotation_type:
                parts.append(f"({ann.annotation_type})")
            if ann.value:
                parts.append(ann.value)
            if ann.notes:
                parts.append(f"— {ann.notes}")
            if ann.metadata and ann.metadata.get("translation_hint"):
                parts.append(f"[Hint: {ann.metadata['translation_hint']}]")

            if parts:
                formatted_lines.append(f"  ^ {' '.join(parts)}")
        formatted_lines.append("")

    return "\n".join(formatted_lines).strip()


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
        Combined scene summary text, or fallback message if none available.
    """
    if not scene_summaries:
        return "(No scene context available)"

    # Get unique scene IDs from lines
    scene_ids: set[SceneId] = {
        line.scene_id for line in lines if line.scene_id is not None
    }

    if not scene_ids:
        return "(No scene context available)"

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

    if not relevant_summaries:
        return "(No scene context available)"

    return "\n".join(relevant_summaries)


def format_pretranslation_annotations(
    lines: list[SourceLine],
    annotations: list[PretranslationAnnotation] | None,
) -> str:
    """Format pretranslation annotations for the lines being translated.

    Filters to only annotations for the given lines and formats them
    for prompt injection.

    Args:
        lines: Source lines being translated.
        annotations: Available pretranslation annotations.

    Returns:
        Formatted annotation text, or fallback message if none available.
    """
    if not annotations:
        return "(No pretranslation notes)"

    # Get line IDs from the current batch
    line_ids: set[LineId] = {line.line_id for line in lines}

    # Filter annotations to just the relevant lines
    relevant_annotations = [ann for ann in annotations if ann.line_id in line_ids]

    if not relevant_annotations:
        return "(No pretranslation notes)"

    # Format each annotation
    formatted: list[str] = []
    for ann in relevant_annotations:
        line_info = f"[{ann.line_id}]"
        type_info = f"({ann.annotation_type})" if ann.annotation_type else ""
        value_info = f": {ann.value}" if ann.value else ""
        notes_info = f" — {ann.notes}" if ann.notes else ""

        # Include translation hint from metadata if available
        hint = ""
        if ann.metadata and ann.metadata.get("translation_hint"):
            hint = f" (Hint: {ann.metadata['translation_hint']})"

        formatted.append(f"{line_info} {type_info}{value_info}{notes_info}{hint}")

    return "\n".join(formatted)


def format_glossary_terms(glossary: list[GlossaryTerm] | None) -> str:
    """Format glossary terms for prompt injection.

    Args:
        glossary: Available glossary terms.

    Returns:
        Formatted glossary text, or fallback message if none available.
    """
    if not glossary:
        return "(No glossary terms)"

    formatted: list[str] = []
    for term in glossary:
        if term.notes:
            formatted.append(f"• {term.term} → {term.translation} ({term.notes})")
        else:
            formatted.append(f"• {term.term} → {term.translation}")

    return "\n".join(formatted)


def translation_result_to_lines(
    result: TranslationResultList,
    source_lines: list[SourceLine],
) -> list[TranslatedLine]:
    """Convert LLM TranslationResultList to TranslatedLine records.

    Copies metadata from source lines (route_id, scene_id, speaker, source_columns)
    and sets source_text from the original source line.

    Args:
        result: Translation result list from the LLM.
        source_lines: Original source lines for metadata lookup.

    Returns:
        List of TranslatedLine records with metadata preserved.

    Raises:
        ValueError: If translated line_ids do not align with source line_ids.
    """
    # Build lookup map for source lines by line_id
    source_map: dict[LineId, SourceLine] = {line.line_id: line for line in source_lines}

    expected_ids = [line.line_id for line in source_lines]
    actual_ids = [translation.line_id for translation in result.translations]
    duplicates = [
        line_id for line_id, count in Counter(actual_ids).items() if count > 1
    ]
    missing = [line_id for line_id in expected_ids if line_id not in set(actual_ids)]
    extra = [line_id for line_id in actual_ids if line_id not in set(expected_ids)]
    if duplicates or missing or extra:
        parts = [
            "Translation alignment error: output IDs must match input IDs.",
            f"Expected {len(expected_ids)} line_id(s), got {len(actual_ids)}.",
        ]
        if missing:
            parts.append(f"Missing: {', '.join(missing)}")
        if extra:
            parts.append(f"Extra: {', '.join(extra)}")
        if duplicates:
            parts.append(f"Duplicate: {', '.join(duplicates)}")
        raise ValueError(" ".join(parts))

    translation_map = {
        translation.line_id: translation for translation in result.translations
    }

    translated_lines: list[TranslatedLine] = []
    for line_id in expected_ids:
        translation = translation_map[line_id]
        source_line = source_map.get(line_id)
        if source_line is None:
            translated_lines.append(
                TranslatedLine(line_id=translation.line_id, text=translation.text)
            )
            continue
        translated_lines.append(
            TranslatedLine(
                line_id=translation.line_id,
                route_id=source_line.route_id,
                scene_id=source_line.scene_id,
                speaker=source_line.speaker,
                source_text=source_line.text,
                text=translation.text,
                metadata=source_line.metadata,
                source_columns=source_line.source_columns,
            )
        )

    return translated_lines


def merge_translated_lines(
    run_id: RunId,
    target_language: LanguageCode,
    translated_lines: list[TranslatedLine],
) -> TranslatePhaseOutput:
    """Package translated lines into TranslatePhaseOutput.

    Args:
        run_id: Run identifier.
        target_language: Target language code.
        translated_lines: List of translated lines from all chunks.

    Returns:
        Complete translate phase output.
    """
    return TranslatePhaseOutput(
        run_id=run_id,
        target_language=target_language,
        translated_lines=translated_lines,
    )
