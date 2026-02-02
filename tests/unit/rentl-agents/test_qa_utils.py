"""Unit tests for QA phase utilities."""

from __future__ import annotations

from uuid import uuid7

import pytest

from rentl_agents.qa import (
    build_qa_summary,
    chunk_qa_lines,
    empty_qa_output,
    format_lines_for_qa_prompt,
    get_scene_summary_for_qa,
    merge_qa_agent_outputs,
    violation_to_qa_issue,
)
from rentl_schemas.io import SourceLine, TranslatedLine
from rentl_schemas.phases import SceneSummary, StyleGuideViolation
from rentl_schemas.primitives import QaCategory, QaSeverity
from rentl_schemas.qa import QaIssue


class TestChunkQaLines:
    """Test cases for chunk_qa_lines function."""

    def test_chunk_single_chunk(self) -> None:
        """Test chunking when all lines fit in one chunk."""
        source_lines = [
            SourceLine(line_id="line_1", text="Hello"),
            SourceLine(line_id="line_2", text="World"),
        ]
        translated_lines = [
            TranslatedLine(line_id="line_1", text="Hola", source_text="Hello"),
            TranslatedLine(line_id="line_2", text="Mundo", source_text="World"),
        ]

        chunks = chunk_qa_lines(source_lines, translated_lines, chunk_size=10)

        assert len(chunks) == 1
        assert len(chunks[0][0]) == 2  # source lines
        assert len(chunks[0][1]) == 2  # translated lines

    def test_chunk_multiple_chunks(self) -> None:
        """Test chunking into multiple chunks."""
        source_lines = [
            SourceLine(line_id=f"line_{i}", text=f"Line {i}") for i in range(10)
        ]
        translated_lines = [
            TranslatedLine(
                line_id=f"line_{i}", text=f"Translated {i}", source_text=f"Line {i}"
            )
            for i in range(10)
        ]

        chunks = chunk_qa_lines(source_lines, translated_lines, chunk_size=3)

        assert len(chunks) == 4  # 3 + 3 + 3 + 1
        assert len(chunks[0][0]) == 3
        assert len(chunks[3][0]) == 1

    def test_chunk_empty_input(self) -> None:
        """Test chunking empty input."""
        chunks = chunk_qa_lines([], [], chunk_size=10)

        assert chunks == []

    def test_chunk_size_zero_raises(self) -> None:
        """Test that chunk_size=0 raises error."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_qa_lines([], [], chunk_size=0)

    def test_chunk_mismatched_lengths_raises(self) -> None:
        """Test that mismatched line counts raise error."""
        source_lines = [SourceLine(line_id="line_1", text="Hello")]
        translated_lines: list[TranslatedLine] = []

        with pytest.raises(ValueError, match="must match"):
            chunk_qa_lines(source_lines, translated_lines, chunk_size=10)


class TestFormatLinesForQaPrompt:
    """Test cases for format_lines_for_qa_prompt function."""

    def test_format_with_speakers(self) -> None:
        """Test formatting lines with speakers."""
        source_lines = [
            SourceLine(
                line_id="line_001",
                text="こんにちは",
                speaker="田中",
            ),
        ]
        translated_lines = [
            TranslatedLine(
                line_id="line_001",
                text="Hello",
                source_text="こんにちは",
            ),
        ]

        result = format_lines_for_qa_prompt(source_lines, translated_lines)

        assert "[line_001]" in result
        assert "[田中]" in result
        assert "Source: こんにちは" in result
        assert "Translation: Hello" in result

    def test_format_without_speakers(self) -> None:
        """Test formatting lines without speakers."""
        source_lines = [
            SourceLine(line_id="line_001", text="Narration"),
        ]
        translated_lines = [
            TranslatedLine(
                line_id="line_001",
                text="Translated narration",
                source_text="Narration",
            ),
        ]

        result = format_lines_for_qa_prompt(source_lines, translated_lines)

        assert "[line_001]" in result
        assert "Source: Narration" in result
        assert "Translation: Translated narration" in result

    def test_format_missing_translation(self) -> None:
        """Test formatting when translation is missing."""
        source_lines = [
            SourceLine(line_id="line_001", text="Hello"),
        ]
        translated_lines: list[TranslatedLine] = []  # No translations

        result = format_lines_for_qa_prompt(source_lines, translated_lines)

        assert "[MISSING TRANSLATION]" in result

    def test_format_empty_lines(self) -> None:
        """Test formatting empty list."""
        result = format_lines_for_qa_prompt([], [])

        assert result == ""


class TestGetSceneSummaryForQa:
    """Test cases for get_scene_summary_for_qa function."""

    def test_get_summary_single_scene(self) -> None:
        """Test getting summary for single scene."""
        source_lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
        ]
        summaries = [
            SceneSummary(
                scene_id="scene_001",
                summary="Scene summary",
                characters=["Alice"],
            ),
        ]

        result = get_scene_summary_for_qa(source_lines, summaries)

        assert "scene_001" in result
        assert "Scene summary" in result

    def test_get_summary_no_summaries(self) -> None:
        """Test when no summaries available."""
        source_lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
        ]

        result = get_scene_summary_for_qa(source_lines, None)

        assert result == ""


class TestViolationToQaIssue:
    """Test cases for violation_to_qa_issue function."""

    def test_convert_basic_violation(self) -> None:
        """Test converting a basic style guide violation."""
        violation = StyleGuideViolation(
            line_id="line_001",
            violation_type="honorific",
            rule_violated="Preserve Japanese honorifics",
            source_text="田中さん",
            translation_text="Mr. Tanaka",
            explanation="Honorific -san was anglicized to Mr.",
            suggestion="Use 'Tanaka-san' instead",
        )

        result = violation_to_qa_issue(violation)

        assert result.line_id == "line_001"
        assert result.category == QaCategory.STYLE
        assert result.severity == QaSeverity.MAJOR  # default
        assert "Preserve Japanese honorifics" in result.message
        assert result.suggestion == "Use 'Tanaka-san' instead"

    def test_convert_with_custom_severity(self) -> None:
        """Test converting with custom severity."""
        violation = StyleGuideViolation(
            line_id="line_002",
            violation_type="formality",
            rule_violated="Match formality level",
            source_text="ありがとうございます",
            translation_text="Thanks!",
            explanation="Formal speech translated as casual",
        )

        result = violation_to_qa_issue(violation, severity=QaSeverity.CRITICAL)

        assert result.severity == QaSeverity.CRITICAL

    def test_convert_generates_unique_id(self) -> None:
        """Test that each conversion generates unique issue_id."""
        violation = StyleGuideViolation(
            line_id="line_001",
            violation_type="other",
            rule_violated="Test rule",
            source_text="Test",
            translation_text="Test",
            explanation="Test explanation",
        )

        result1 = violation_to_qa_issue(violation)
        result2 = violation_to_qa_issue(violation)

        assert result1.issue_id != result2.issue_id

    def test_convert_includes_metadata(self) -> None:
        """Test that metadata includes violation details."""
        violation = StyleGuideViolation(
            line_id="line_001",
            violation_type="terminology",
            rule_violated="Use glossary terms",
            source_text="Source text",
            translation_text="Translation",
            explanation="Wrong term used",
        )

        result = violation_to_qa_issue(violation)

        assert result.metadata is not None
        assert result.metadata.get("violation_type") == "terminology"
        assert result.metadata.get("source_text") == "Source text"
        assert result.metadata.get("translation_text") == "Translation"


class TestBuildQaSummary:
    """Test cases for build_qa_summary function."""

    def test_build_summary_empty(self) -> None:
        """Test building summary from empty issues list."""
        result = build_qa_summary([])

        assert result.total_issues == 0
        assert result.by_category == {}
        assert result.by_severity == {}

    def test_build_summary_single_issue(self) -> None:
        """Test building summary from single issue."""
        issues = [
            QaIssue(
                issue_id=uuid7(),
                line_id="line_001",
                category=QaCategory.STYLE,
                severity=QaSeverity.MAJOR,
                message="Test issue",
            ),
        ]

        result = build_qa_summary(issues)

        assert result.total_issues == 1
        assert result.by_category == {QaCategory.STYLE: 1}
        assert result.by_severity == {QaSeverity.MAJOR: 1}

    def test_build_summary_multiple_categories(self) -> None:
        """Test building summary with multiple categories."""
        issues = [
            QaIssue(
                issue_id=uuid7(),
                line_id="line_001",
                category=QaCategory.STYLE,
                severity=QaSeverity.MAJOR,
                message="Style issue",
            ),
            QaIssue(
                issue_id=uuid7(),
                line_id="line_002",
                category=QaCategory.FORMATTING,
                severity=QaSeverity.MINOR,
                message="Formatting issue",
            ),
            QaIssue(
                issue_id=uuid7(),
                line_id="line_003",
                category=QaCategory.STYLE,
                severity=QaSeverity.CRITICAL,
                message="Another style issue",
            ),
        ]

        result = build_qa_summary(issues)

        assert result.total_issues == 3
        assert result.by_category[QaCategory.STYLE] == 2
        assert result.by_category[QaCategory.FORMATTING] == 1
        assert result.by_severity[QaSeverity.MAJOR] == 1
        assert result.by_severity[QaSeverity.MINOR] == 1
        assert result.by_severity[QaSeverity.CRITICAL] == 1


class TestMergeQaAgentOutputs:
    """Test cases for merge_qa_agent_outputs function."""

    def test_merge_multiple_issues(self) -> None:
        """Test merging multiple QA issues."""
        run_id = uuid7()
        issues = [
            QaIssue(
                issue_id=uuid7(),
                line_id="line_001",
                category=QaCategory.STYLE,
                severity=QaSeverity.MAJOR,
                message="Issue 1",
            ),
            QaIssue(
                issue_id=uuid7(),
                line_id="line_002",
                category=QaCategory.STYLE,
                severity=QaSeverity.MINOR,
                message="Issue 2",
            ),
        ]

        result = merge_qa_agent_outputs(run_id, issues, "en")

        assert result.run_id == run_id
        assert result.target_language == "en"
        assert len(result.issues) == 2
        assert result.summary.total_issues == 2

    def test_merge_empty_issues(self) -> None:
        """Test merging empty list of issues."""
        run_id = uuid7()

        result = merge_qa_agent_outputs(run_id, [], "en")

        assert result.run_id == run_id
        assert result.issues == []
        assert result.summary.total_issues == 0


class TestEmptyQaOutput:
    """Test cases for empty_qa_output function."""

    def test_creates_empty_output(self) -> None:
        """Test creating empty QA output."""
        run_id = uuid7()

        result = empty_qa_output(run_id, "en")

        assert result.run_id == run_id
        assert result.target_language == "en"
        assert result.issues == []
        assert result.summary.total_issues == 0
        assert result.summary.by_category == {}
        assert result.summary.by_severity == {}
