"""Unit tests for phase explanation module."""

from __future__ import annotations

import pytest

from rentl_core.explain import PhaseInfo, get_phase_info, list_phases
from rentl_schemas.primitives import PhaseName


class TestPhaseInfo:
    """Tests for PhaseInfo model."""

    def test_phase_info_creation(self) -> None:
        """PhaseInfo can be created with all required fields."""
        info = PhaseInfo(
            name=PhaseName.INGEST,
            description="Parse source files",
            inputs=["Source files"],
            outputs=["Scene database"],
            prerequisites=["Valid source files"],
            config_options=["ingest.format"],
        )
        assert info.name == PhaseName.INGEST
        assert info.description == "Parse source files"
        assert "Source files" in info.inputs
        assert "Scene database" in info.outputs
        assert "Valid source files" in info.prerequisites
        assert "ingest.format" in info.config_options

    def test_phase_info_empty_description_fails(self) -> None:
        """PhaseInfo requires non-empty description."""
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            PhaseInfo(
                name=PhaseName.INGEST,
                description="",
                inputs=["Source files"],
                outputs=["Scene database"],
                prerequisites=["Valid source files"],
                config_options=["ingest.format"],
            )


class TestGetPhaseInfo:
    """Tests for get_phase_info function."""

    def test_get_phase_info_with_enum(self) -> None:
        """get_phase_info returns info when given PhaseName enum."""
        info = get_phase_info(PhaseName.INGEST)
        assert info.name == PhaseName.INGEST
        assert len(info.description) > 0
        assert len(info.inputs) > 0
        assert len(info.outputs) > 0
        assert len(info.prerequisites) > 0
        assert len(info.config_options) > 0

    def test_get_phase_info_with_string(self) -> None:
        """get_phase_info returns info when given valid string."""
        info = get_phase_info("ingest")
        assert info.name == PhaseName.INGEST
        assert len(info.description) > 0

    def test_get_phase_info_invalid_string(self) -> None:
        """get_phase_info raises ValueError for invalid phase name."""
        with pytest.raises(ValueError, match="Invalid phase name 'badphase'"):
            get_phase_info("badphase")

    def test_get_phase_info_invalid_error_includes_valid_phases(self) -> None:
        """get_phase_info error message lists valid phases."""
        with pytest.raises(ValueError, match=r"Valid phases:.*ingest"):
            get_phase_info("badphase")

    @pytest.mark.parametrize(
        "phase",
        [
            PhaseName.INGEST,
            PhaseName.CONTEXT,
            PhaseName.PRETRANSLATION,
            PhaseName.TRANSLATE,
            PhaseName.QA,
            PhaseName.EDIT,
            PhaseName.EXPORT,
        ],
    )
    def test_all_phases_have_complete_info(self, phase: PhaseName) -> None:
        """All 7 phases have complete information."""
        info = get_phase_info(phase)
        assert info.name == phase
        assert len(info.description) > 0
        assert len(info.inputs) > 0
        assert len(info.outputs) > 0
        assert len(info.prerequisites) > 0
        assert len(info.config_options) > 0

    def test_ingest_phase_content(self) -> None:
        """Ingest phase has expected content."""
        info = get_phase_info(PhaseName.INGEST)
        assert (
            "parse" in info.description.lower() or "ingest" in info.description.lower()
        )
        assert any("source" in inp.lower() for inp in info.inputs)
        assert any(
            "scene" in out.lower() or "database" in out.lower() for out in info.outputs
        )

    def test_context_phase_content(self) -> None:
        """Context phase has expected content."""
        info = get_phase_info(PhaseName.CONTEXT)
        assert (
            "context" in info.description.lower()
            or "analyze" in info.description.lower()
        )
        assert any(
            "llm" in prereq.lower() or "endpoint" in prereq.lower()
            for prereq in info.prerequisites
        )

    def test_translate_phase_content(self) -> None:
        """Translate phase has expected content."""
        info = get_phase_info(PhaseName.TRANSLATE)
        assert "translat" in info.description.lower()
        assert any(
            "target" in inp.lower() or "language" in inp.lower() for inp in info.inputs
        )

    def test_export_phase_content(self) -> None:
        """Export phase has expected content."""
        info = get_phase_info(PhaseName.EXPORT)
        assert "export" in info.description.lower()
        assert any(
            "output" in out.lower() or "file" in out.lower() for out in info.outputs
        )


class TestListPhases:
    """Tests for list_phases function."""

    def test_list_phases_returns_all_seven(self) -> None:
        """list_phases returns all 7 phases."""
        phases = list_phases()
        assert len(phases) == 7

    def test_list_phases_returns_tuples(self) -> None:
        """list_phases returns list of (PhaseName, description) tuples."""
        phases = list_phases()
        for phase, description in phases:
            assert isinstance(phase, PhaseName)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_list_phases_includes_all_phase_names(self) -> None:
        """list_phases includes all PhaseName enum values."""
        phases = list_phases()
        phase_names = {phase for phase, _ in phases}
        expected_names = {
            PhaseName.INGEST,
            PhaseName.CONTEXT,
            PhaseName.PRETRANSLATION,
            PhaseName.TRANSLATE,
            PhaseName.QA,
            PhaseName.EDIT,
            PhaseName.EXPORT,
        }
        assert phase_names == expected_names

    def test_list_phases_descriptions_non_empty(self) -> None:
        """list_phases returns non-empty descriptions for all phases."""
        phases = list_phases()
        for _, description in phases:
            assert len(description) > 0
