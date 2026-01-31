"""Unit tests for context phase utilities."""

from __future__ import annotations

from uuid import uuid7

import pytest

from rentl_agents.context import (
    SceneValidationError,
    format_scene_lines,
    group_lines_by_scene,
    merge_scene_summaries,
    validate_scene_input,
)
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import SceneSummary


class TestValidateSceneInput:
    """Test cases for validate_scene_input function."""

    def test_valid_input_with_scene_ids(self) -> None:
        """Test validation passes when all lines have scene_id."""
        lines = [
            SourceLine(line_id="line_1", text="Hello", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="World", scene_id="scene_001"),
        ]

        # Should not raise
        validate_scene_input(lines)

    def test_missing_scene_id_raises(self) -> None:
        """Test validation raises when line missing scene_id."""
        lines = [
            SourceLine(line_id="line_1", text="Hello", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="World", scene_id=None),
        ]

        with pytest.raises(SceneValidationError) as exc_info:
            validate_scene_input(lines)

        assert exc_info.value.missing_count == 1
        assert "line_2" in exc_info.value.line_ids

    def test_multiple_missing_scene_ids(self) -> None:
        """Test validation reports multiple missing scene_ids."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id=None),
            SourceLine(line_id="line_2", text="B", scene_id=None),
            SourceLine(line_id="line_3", text="C", scene_id=None),
        ]

        with pytest.raises(SceneValidationError) as exc_info:
            validate_scene_input(lines)

        assert exc_info.value.missing_count == 3

    def test_error_message_suggests_batch_summarizer(self) -> None:
        """Test error message mentions BatchSummarizer alternative."""
        lines = [SourceLine(line_id="line_1", text="A", scene_id=None)]

        with pytest.raises(SceneValidationError) as exc_info:
            validate_scene_input(lines)

        assert "BatchSummarizer" in str(exc_info.value)

    def test_empty_input_passes(self) -> None:
        """Test validation passes for empty input."""
        validate_scene_input([])


class TestGroupLinesByScene:
    """Test cases for group_lines_by_scene function."""

    def test_group_single_scene(self) -> None:
        """Test grouping lines from single scene."""
        lines = [
            SourceLine(line_id="line_1", text="Hello", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="World", scene_id="scene_001"),
        ]

        groups = group_lines_by_scene(lines)

        assert len(groups) == 1
        assert "scene_001" in groups
        assert len(groups["scene_001"]) == 2

    def test_group_multiple_scenes(self) -> None:
        """Test grouping lines from multiple scenes."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="B", scene_id="scene_002"),
            SourceLine(line_id="line_3", text="C", scene_id="scene_001"),
        ]

        groups = group_lines_by_scene(lines)

        assert len(groups) == 2
        assert len(groups["scene_001"]) == 2
        assert len(groups["scene_002"]) == 1

    def test_skip_lines_without_scene_id(self) -> None:
        """Test lines without scene_id are skipped."""
        lines = [
            SourceLine(line_id="line_1", text="A", scene_id="scene_001"),
            SourceLine(line_id="line_2", text="B", scene_id=None),
        ]

        groups = group_lines_by_scene(lines)

        assert len(groups) == 1
        assert len(groups["scene_001"]) == 1

    def test_empty_input(self) -> None:
        """Test grouping empty input."""
        groups = group_lines_by_scene([])

        assert groups == {}


class TestFormatSceneLines:
    """Test cases for format_scene_lines function."""

    def test_format_with_speakers(self) -> None:
        """Test formatting lines with speakers."""
        lines = [
            SourceLine(
                line_id="line_1",
                text="Hello there!",
                speaker="Alice",
                scene_id="scene_001",
            ),
            SourceLine(
                line_id="line_2",
                text="Hi!",
                speaker="Bob",
                scene_id="scene_001",
            ),
        ]

        result = format_scene_lines(lines)

        assert "[Alice]: Hello there!" in result
        assert "[Bob]: Hi!" in result

    def test_format_without_speakers(self) -> None:
        """Test formatting lines without speakers."""
        lines = [
            SourceLine(
                line_id="line_1",
                text="Narration text",
                scene_id="scene_001",
            ),
        ]

        result = format_scene_lines(lines)

        assert result == "Narration text"
        assert "[" not in result

    def test_format_mixed_speakers(self) -> None:
        """Test formatting mix of lines with and without speakers."""
        lines = [
            SourceLine(
                line_id="line_1",
                text="Chapter 1",
                scene_id="scene_001",
            ),
            SourceLine(
                line_id="line_2",
                text="Hello!",
                speaker="Alice",
                scene_id="scene_001",
            ),
        ]

        result = format_scene_lines(lines)

        assert "Chapter 1" in result
        assert "[Alice]: Hello!" in result

    def test_format_empty_lines(self) -> None:
        """Test formatting empty list."""
        result = format_scene_lines([])

        assert result == ""


class TestMergeSceneSummaries:
    """Test cases for merge_scene_summaries function."""

    def test_merge_summaries(self) -> None:
        """Test merging multiple scene summaries."""
        run_id = uuid7()  # Pass UUID directly, not str
        summaries = [
            SceneSummary(
                scene_id="scene_001",
                summary="First scene summary",
                characters=["Alice"],
            ),
            SceneSummary(
                scene_id="scene_002",
                summary="Second scene summary",
                characters=["Bob"],
            ),
        ]

        result = merge_scene_summaries(run_id, summaries)

        assert result.run_id == run_id
        assert len(result.scene_summaries) == 2
        assert result.context_notes == []

    def test_merge_empty_summaries(self) -> None:
        """Test merging empty list of summaries."""
        run_id = uuid7()  # Pass UUID directly, not str

        result = merge_scene_summaries(run_id, [])

        assert result.run_id == run_id
        assert result.scene_summaries == []
