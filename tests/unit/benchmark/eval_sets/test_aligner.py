"""Unit tests for LineAligner."""

import pytest

from rentl_core.benchmark.eval_sets.aligner import LineAligner
from rentl_schemas.io import SourceLine


class TestLineAligner:
    """Test suite for line alignment."""

    @pytest.fixture
    def aligner(self) -> LineAligner:
        """Create a fresh aligner instance.

        Returns:
            LineAligner instance
        """
        return LineAligner()

    @pytest.fixture
    def source_lines(self) -> list[SourceLine]:
        """Sample source lines.

        Returns:
            List of sample source language lines
        """
        return [
            SourceLine(line_id="scene_1", scene_id="scene_1", text="おはよう"),
            SourceLine(line_id="scene_2", scene_id="scene_1", text="こんにちは"),
            SourceLine(line_id="scene_3", scene_id="scene_1", text="こんばんは"),
        ]

    @pytest.fixture
    def reference_lines(self) -> list[SourceLine]:
        """Sample reference lines.

        Returns:
            List of sample reference translation lines
        """
        return [
            SourceLine(line_id="scene_1", scene_id="scene_1", text="Good morning"),
            SourceLine(line_id="scene_2", scene_id="scene_1", text="Hello"),
            SourceLine(line_id="scene_3", scene_id="scene_1", text="Good evening"),
        ]

    def test_align_by_id_perfect_match(
        self,
        aligner: LineAligner,
        source_lines: list[SourceLine],
        reference_lines: list[SourceLine],
    ) -> None:
        """Aligner correctly matches lines by ID."""
        aligned = aligner.align_by_id(source_lines, reference_lines)

        assert len(aligned) == 3
        assert aligned[0].source.text == "おはよう"
        assert aligned[0].reference is not None
        assert aligned[0].reference.text == "Good morning"
        assert aligned[1].source.text == "こんにちは"
        assert aligned[1].reference is not None
        assert aligned[1].reference.text == "Hello"

    def test_align_by_id_missing_reference(
        self,
        aligner: LineAligner,
        source_lines: list[SourceLine],
    ) -> None:
        """Aligner handles missing reference lines."""
        partial_refs = [
            SourceLine(line_id="scene_1", scene_id="scene_1", text="Good morning"),
        ]
        aligned = aligner.align_by_id(source_lines, partial_refs)

        assert len(aligned) == 3
        assert aligned[0].reference is not None
        assert aligned[0].reference.text == "Good morning"
        assert aligned[1].reference is None
        assert aligned[2].reference is None

    def test_align_by_position(
        self,
        aligner: LineAligner,
        source_lines: list[SourceLine],
        reference_lines: list[SourceLine],
    ) -> None:
        """Aligner aligns by position when IDs don't match."""
        aligned = aligner.align_by_position(source_lines, reference_lines)

        assert len(aligned) == 3
        for idx in range(3):
            assert aligned[idx].source == source_lines[idx]
            assert aligned[idx].reference == reference_lines[idx]

    def test_align_by_position_unequal_lengths(
        self,
        aligner: LineAligner,
        source_lines: list[SourceLine],
    ) -> None:
        """Aligner handles unequal list lengths in position alignment."""
        short_refs = [
            SourceLine(line_id="scene_1", scene_id="scene_1", text="Good morning"),
        ]
        aligned = aligner.align_by_position(source_lines, short_refs)

        assert len(aligned) == 3
        assert aligned[0].reference is not None
        assert aligned[1].reference is None
        assert aligned[2].reference is None
