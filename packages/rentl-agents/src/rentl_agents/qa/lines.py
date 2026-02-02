"""Line utilities for QA phase.

This module provides:
- Line chunking for batch QA processing
- Line formatting for QA prompt injection
- Violation to QaIssue conversion
- QA output merging
"""

from __future__ import annotations

from uuid import uuid7

from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.phases import (
    QaPhaseOutput,
    SceneSummary,
    StyleGuideViolation,
)
from rentl_schemas.primitives import (
    LanguageCode,
    QaCategory,
    QaSeverity,
    RunId,
    SceneId,
)
from rentl_schemas.qa import QaIssue, QaSummary


def chunk_qa_lines(
    source_lines: list[SourceLine],
    translated_lines: list[TranslatedLine],
    chunk_size: int = 10,
) -> list[tuple[list[SourceLine], list[TranslatedLine]]]:
    """Split source and translated lines into aligned chunks for batch processing.

    Args:
        source_lines: Source lines to chunk.
        translated_lines: Translated lines to chunk (must align with source).
        chunk_size: Maximum lines per chunk (default 10).

    Returns:
        List of tuples, each containing aligned source and translated line chunks.

    Raises:
        ValueError: If chunk_size is not positive or line counts don't match.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if len(source_lines) != len(translated_lines):
        raise ValueError(
            f"Source and translated line counts must match: "
            f"{len(source_lines)} vs {len(translated_lines)}"
        )

    chunks: list[tuple[list[SourceLine], list[TranslatedLine]]] = []
    for i in range(0, len(source_lines), chunk_size):
        source_chunk = source_lines[i : i + chunk_size]
        translated_chunk = translated_lines[i : i + chunk_size]
        chunks.append((source_chunk, translated_chunk))

    return chunks


def format_lines_for_qa_prompt(
    source_lines: list[SourceLine],
    translated_lines: list[TranslatedLine],
) -> str:
    """Format paired source and translated lines for QA prompt injection.

    Creates a readable text block with line IDs, source text, and translations.

    Args:
        source_lines: Source lines with original text.
        translated_lines: Translated lines with translations.

    Returns:
        Formatted string for prompt template.
    """
    # Build a map of line_id to translated text for lookup
    translation_map: dict[str, str] = {
        line.line_id: line.text for line in translated_lines
    }

    formatted_lines: list[str] = []

    for source in source_lines:
        translation = translation_map.get(source.line_id, "[MISSING TRANSLATION]")

        if source.speaker:
            formatted_lines.append(
                f"[{source.line_id}] [{source.speaker}]\n"
                f"  Source: {source.text}\n"
                f"  Translation: {translation}"
            )
        else:
            formatted_lines.append(
                f"[{source.line_id}]\n"
                f"  Source: {source.text}\n"
                f"  Translation: {translation}"
            )

    return "\n\n".join(formatted_lines)


def get_scene_summary_for_qa(
    source_lines: list[SourceLine],
    scene_summaries: list[SceneSummary] | None,
) -> str:
    """Get relevant scene summaries for QA context.

    Looks up scene summaries for all unique scene IDs in the lines.

    Args:
        source_lines: Source lines with optional scene_id.
        scene_summaries: Available scene summaries from context phase.

    Returns:
        Combined scene summary text, or empty string if none available.
    """
    if not scene_summaries:
        return ""

    # Get unique scene IDs from lines
    scene_ids: set[SceneId] = {
        line.scene_id for line in source_lines if line.scene_id is not None
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


def violation_to_qa_issue(
    violation: StyleGuideViolation,
    severity: QaSeverity = QaSeverity.MAJOR,
) -> QaIssue:
    """Convert a StyleGuideViolation to a QaIssue.

    Creates a standardized QA issue with the violation details stored
    in the metadata field.

    Args:
        violation: Style guide violation from the style guide critic.
        severity: Severity level for the issue (default MAJOR).

    Returns:
        QaIssue with category=STYLE.
    """
    return QaIssue(
        issue_id=uuid7(),
        line_id=violation.line_id,
        category=QaCategory.STYLE,
        severity=severity,
        message=f"{violation.rule_violated}: {violation.explanation}",
        suggestion=None,  # Simplified schema - suggestions out of scope
        metadata={
            "rule_violated": violation.rule_violated,
        },
    )


def build_qa_summary(issues: list[QaIssue]) -> QaSummary:
    """Build a QA summary from a list of issues.

    Args:
        issues: List of QA issues to summarize.

    Returns:
        QaSummary with counts by category and severity.
    """
    by_category: dict[QaCategory, int] = {}
    by_severity: dict[QaSeverity, int] = {}

    for issue in issues:
        # Convert string values to enum instances (use_enum_values=True)
        category = (
            QaCategory(issue.category)
            if isinstance(issue.category, str)
            else issue.category
        )
        severity = (
            QaSeverity(issue.severity)
            if isinstance(issue.severity, str)
            else issue.severity
        )
        by_category[category] = by_category.get(category, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1

    return QaSummary(
        total_issues=len(issues),
        by_category=by_category,
        by_severity=by_severity,
    )


def merge_qa_agent_outputs(
    run_id: RunId,
    issues: list[QaIssue],
    target_language: LanguageCode,
) -> QaPhaseOutput:
    """Merge QA issues into a QA phase output.

    Packages all QA issues with a computed summary.

    Args:
        run_id: Run identifier.
        issues: List of QA issues from all chunks.
        target_language: Target language code.

    Returns:
        Complete QA phase output.
    """
    summary = build_qa_summary(issues)

    return QaPhaseOutput(
        run_id=run_id,
        target_language=target_language,
        issues=issues,
        summary=summary,
    )


def empty_qa_output(
    run_id: RunId,
    target_language: LanguageCode,
) -> QaPhaseOutput:
    """Create an empty QA phase output.

    Used when no style guide is provided or no issues are found.

    Args:
        run_id: Run identifier.
        target_language: Target language code.

    Returns:
        QA phase output with empty issues list.
    """
    return QaPhaseOutput(
        run_id=run_id,
        target_language=target_language,
        issues=[],
        summary=QaSummary(
            total_issues=0,
            by_category={},
            by_severity={},
        ),
    )
