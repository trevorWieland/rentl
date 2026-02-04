"""Unit tests for pretranslation phase utilities."""

from __future__ import annotations

from uuid import uuid7

import pytest

from rentl_agents.pretranslation import (
    chunk_lines,
    format_lines_for_prompt,
    get_scene_summary_for_lines,
    idiom_to_annotation,
    merge_idiom_annotations,
)
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import IdiomAnnotation, SceneSummary


class TestChunkLines:
    """Test cases for chunk_lines function."""

    def test_chunk_single_chunk(self) -> None:
        """Test chunking when all lines fit in one chunk."""
        lines = [
            SourceLine(line_id="line_1", text="Hello"),
            SourceLine(line_id="line_2", text="World"),
        ]

        chunks = chunk_lines(lines, chunk_size=10)

        assert len(chunks) == 1
        assert len(chunks[0]) == 2

    def test_chunk_multiple_chunks(self) -> None:
        """Test chunking into multiple chunks."""
        lines = [SourceLine(line_id=f"line_{i}", text=f"Line {i}") for i in range(10)]

        chunks = chunk_lines(lines, chunk_size=3)

        assert len(chunks) == 4  # 3 + 3 + 3 + 1
        assert len(chunks[0]) == 3
        assert len(chunks[1]) == 3
        assert len(chunks[2]) == 3
        assert len(chunks[3]) == 1

    def test_chunk_exact_division(self) -> None:
        """Test chunking when lines divide evenly."""
        lines = [SourceLine(line_id=f"line_{i}", text=f"Line {i}") for i in range(9)]

        chunks = chunk_lines(lines, chunk_size=3)

        assert len(chunks) == 3
        assert all(len(chunk) == 3 for chunk in chunks)

    def test_chunk_empty_input(self) -> None:
        """Test chunking empty input."""
        chunks = chunk_lines([], chunk_size=10)

        assert chunks == []

    def test_chunk_size_one(self) -> None:
        """Test chunking with chunk_size=1."""
        lines = [
            SourceLine(line_id="line_1", text="A"),
            SourceLine(line_id="line_2", text="B"),
        ]

        chunks = chunk_lines(lines, chunk_size=1)

        assert len(chunks) == 2
        assert len(chunks[0]) == 1
        assert len(chunks[1]) == 1

    def test_chunk_size_zero_raises(self) -> None:
        """Test that chunk_size=0 raises error."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_lines([], chunk_size=0)

    def test_chunk_size_negative_raises(self) -> None:
        """Test that negative chunk_size raises error."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_lines([], chunk_size=-1)


class TestFormatLinesForPrompt:
    """Test cases for format_lines_for_prompt function."""

    def test_format_with_speakers(self) -> None:
        """Test formatting lines with speakers."""
        lines = [
            SourceLine(
                line_id="line_001",
                text="Hello there!",
                speaker="Alice",
            ),
            SourceLine(
                line_id="line_002",
                text="Hi!",
                speaker="Bob",
            ),
        ]

        result = format_lines_for_prompt(lines)

        assert "[line_001] [Alice]: Hello there!" in result
        assert "[line_002] [Bob]: Hi!" in result

    def test_format_without_speakers(self) -> None:
        """Test formatting lines without speakers."""
        lines = [
            SourceLine(
                line_id="line_001",
                text="Narration text",
            ),
        ]

        result = format_lines_for_prompt(lines)

        assert "[line_001]: Narration text" in result
        assert "[" in result  # Should have line_id bracket

    def test_format_mixed_speakers(self) -> None:
        """Test formatting mix of lines with and without speakers."""
        lines = [
            SourceLine(
                line_id="line_001",
                text="Chapter 1",
            ),
            SourceLine(
                line_id="line_002",
                text="Hello!",
                speaker="Alice",
            ),
        ]

        result = format_lines_for_prompt(lines)

        assert "[line_001]: Chapter 1" in result
        assert "[line_002] [Alice]: Hello!" in result

    def test_format_empty_lines(self) -> None:
        """Test formatting empty list."""
        result = format_lines_for_prompt([])

        assert not result

    def test_format_preserves_line_ids(self) -> None:
        """Test that line IDs are included in output."""
        lines = [
            SourceLine(line_id="custom_123", text="Test"),
        ]

        result = format_lines_for_prompt(lines)

        assert "custom_123" in result


class TestGetSceneSummaryForLines:
    """Test cases for get_scene_summary_for_lines function."""

    def test_get_summary_single_scene(self) -> None:
        """Test getting summary for single scene."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="B", scene_id="scene_001"),
        ]
        summaries = [
            SceneSummary(
                scene_id="scene_001",
                summary="First scene summary",
                characters=["Alice"],
            ),
        ]

        result = get_scene_summary_for_lines(lines, summaries)

        assert "scene_001" in result
        assert "First scene summary" in result

    def test_get_summary_multiple_scenes(self) -> None:
        """Test getting summaries for multiple scenes."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="B", scene_id="scene_002"),
        ]
        summaries = [
            SceneSummary(
                scene_id="scene_001",
                summary="First summary",
                characters=["Alice"],
            ),
            SceneSummary(
                scene_id="scene_002",
                summary="Second summary",
                characters=["Bob"],
            ),
        ]

        result = get_scene_summary_for_lines(lines, summaries)

        assert "First summary" in result
        assert "Second summary" in result

    def test_get_summary_no_summaries_available(self) -> None:
        """Test when no summaries are available."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
        ]

        result = get_scene_summary_for_lines(lines, None)

        assert not result

    def test_get_summary_empty_summaries(self) -> None:
        """Test when summaries list is empty."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
        ]

        result = get_scene_summary_for_lines(lines, [])

        assert not result

    def test_get_summary_no_scene_ids_in_lines(self) -> None:
        """Test when lines have no scene_id."""
        lines = [
            SourceLine(line_id="line_1", text="A"),
            SourceLine(line_id="line_2", text="B"),
        ]
        summaries = [
            SceneSummary(
                scene_id="scene_001",
                summary="First summary",
                characters=["Alice"],
            ),
        ]

        result = get_scene_summary_for_lines(lines, summaries)

        assert not result

    def test_get_summary_missing_scene_in_summaries(self) -> None:
        """Test when scene_id not found in summaries."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_999"),
        ]
        summaries = [
            SceneSummary(
                scene_id="scene_001",
                summary="First summary",
                characters=["Alice"],
            ),
        ]

        result = get_scene_summary_for_lines(lines, summaries)

        assert not result


class TestIdiomToAnnotation:
    """Test cases for idiom_to_annotation function."""

    def test_convert_basic_idiom(self) -> None:
        """Test converting a basic idiom annotation."""
        idiom = IdiomAnnotation(
            line_id="line_001",
            idiom_text="猫の手も借りたい",
            explanation="A phrase meaning extremely busy",
        )

        result = idiom_to_annotation(idiom)

        assert result.line_id == "line_001"
        assert result.annotation_type == "idiom"
        assert result.value == "猫の手も借りたい"
        assert result.notes == "A phrase meaning extremely busy"

    def test_convert_idiom_preserves_explanation(self) -> None:
        """Test converting idiom preserves explanation in notes."""
        idiom = IdiomAnnotation(
            line_id="line_002",
            idiom_text="It's raining cats and dogs",
            explanation="Heavy rain idiom",
        )

        result = idiom_to_annotation(idiom)

        assert result.line_id == "line_002"
        assert result.value == "It's raining cats and dogs"
        assert result.notes == "Heavy rain idiom"

    def test_convert_idiom_generates_unique_id(self) -> None:
        """Test that each conversion generates unique annotation_id."""
        idiom = IdiomAnnotation(
            line_id="line_001",
            idiom_text="Test",
            explanation="Test",
        )

        result1 = idiom_to_annotation(idiom)
        result2 = idiom_to_annotation(idiom)

        assert result1.annotation_id != result2.annotation_id


class TestMergeIdiomAnnotations:
    """Test cases for merge_idiom_annotations function."""

    def test_merge_multiple_idioms(self) -> None:
        """Test merging multiple idiom annotations."""
        run_id = uuid7()
        idioms = [
            IdiomAnnotation(
                line_id="line_001",
                idiom_text="Idiom 1",
                explanation="First idiom",
            ),
            IdiomAnnotation(
                line_id="line_002",
                idiom_text="Idiom 2",
                explanation="Second idiom",
            ),
        ]

        result = merge_idiom_annotations(run_id, idioms)

        assert result.run_id == run_id
        assert len(result.annotations) == 2
        assert result.term_candidates == []

    def test_merge_empty_idioms(self) -> None:
        """Test merging empty list of idioms."""
        run_id = uuid7()

        result = merge_idiom_annotations(run_id, [])

        assert result.run_id == run_id
        assert result.annotations == []
        assert result.term_candidates == []

    def test_merge_preserves_idiom_details(self) -> None:
        """Test that merge preserves all idiom details."""
        run_id = uuid7()
        idioms = [
            IdiomAnnotation(
                line_id="line_001",
                idiom_text="Test idiom",
                explanation="Cultural explanation",
            ),
        ]

        result = merge_idiom_annotations(run_id, idioms)

        annotation = result.annotations[0]
        assert annotation.value == "Test idiom"
        assert annotation.notes == "Cultural explanation"
        # Simplified schema - no type categorization or hints needed
