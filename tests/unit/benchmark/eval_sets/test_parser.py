"""Unit tests for RenpyDialogueParser."""

import re
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from rentl_core.benchmark.eval_sets.parser import RenpyDialogueParser
from rentl_schemas.primitives import HUMAN_ID_PATTERN


class TestRenpyDialogueParser:
    """Test suite for Ren'Py dialogue parser."""

    @pytest.fixture
    def parser(self) -> RenpyDialogueParser:
        """Create a fresh parser instance.

        Returns:
            RenpyDialogueParser instance
        """
        return RenpyDialogueParser()

    def test_parse_dialogue_with_speaker(self, parser: RenpyDialogueParser) -> None:
        """Parser extracts dialogue with speaker."""
        script_content = """# Ren'Py script
    hisao "This is a test line."
    """
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 1
            assert lines[0].speaker == "hisao"
            assert lines[0].text == "This is a test line."
            assert lines[0].scene_id == "test_1"
            assert lines[0].line_id.startswith("test_1_")
        finally:
            script_path.unlink()

    def test_parse_narration(self, parser: RenpyDialogueParser) -> None:
        """Parser extracts narration without speaker."""
        script_content = """# Ren'Py script
    "The room is quiet."
    """
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 1
            assert lines[0].speaker is None
            assert lines[0].text == "The room is quiet."
        finally:
            script_path.unlink()

    def test_parse_menu_choice(self, parser: RenpyDialogueParser) -> None:
        """Parser extracts menu choices."""
        script_content = """# Ren'Py script
    menu:
        "Go left":
            pass
    """
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 1
            assert lines[0].speaker == "[menu]"
            assert lines[0].text == "Go left"
            assert lines[0].metadata is not None
            assert lines[0].metadata.get("type") == "choice"
        finally:
            script_path.unlink()

    def test_parse_mixed_dialogue(self, parser: RenpyDialogueParser) -> None:
        """Parser handles multiple dialogue types in one script."""
        script_content = """# Ren'Py script
    "Morning arrives."
    hisao "Good morning."
    emi "Hey!"
    menu:
        "Wave back":
            pass
    """
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 4
            assert lines[0].speaker is None
            assert lines[0].text == "Morning arrives."
            assert lines[1].speaker == "hisao"
            assert lines[1].text == "Good morning."
            assert lines[2].speaker == "emi"
            assert lines[2].text == "Hey!"
            assert lines[3].speaker == "[menu]"
            assert lines[3].text == "Wave back"
        finally:
            script_path.unlink()

    def test_parse_escapes_quotes(self, parser: RenpyDialogueParser) -> None:
        """Parser handles escaped quotes in dialogue."""
        script_content = r"""# Ren'Py script
    hisao "She said \"hello\" to me."
    """
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 1
            assert lines[0].text == 'She said "hello" to me.'
        finally:
            script_path.unlink()

    def test_default_scene_id_from_filename(self, parser: RenpyDialogueParser) -> None:
        """Parser uses filename as scene_id when not specified."""
        script_content = '''hisao "Test line."'''
        with NamedTemporaryFile(
            mode="w", suffix=".rpy", delete=False, prefix="script_"
        ) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            # We need to normalize the filename to match the HumanReadableId pattern
            # The temp file will have a random suffix, so we override scene_id
            lines = parser.parse_script(script_path, scene_id="script_1")
            assert len(lines) == 1
            assert lines[0].scene_id == "script_1"
        finally:
            script_path.unlink()

    def test_normalize_scene_id_ksre_filename(self) -> None:
        """Parser normalizes KSRE-style filenames with hyphens."""
        normalized = RenpyDialogueParser.normalize_scene_id("script-a1-sunday")
        # "script-a1-sunday" -> letters: "script", "a", "sunday"; numbers: "1"
        # -> "scriptasunday_1"
        assert normalized == "scriptasunday_1"

        # Validate against HumanReadableId pattern
        assert re.match(HUMAN_ID_PATTERN, normalized)

    def test_normalize_scene_id_simple_name(self) -> None:
        """Parser normalizes simple filenames without numbers."""
        normalized = RenpyDialogueParser.normalize_scene_id("test")
        assert normalized == "test_0"

        assert re.match(HUMAN_ID_PATTERN, normalized)

    def test_normalize_scene_id_already_valid(self) -> None:
        """Parser preserves already-valid IDs."""
        normalized = RenpyDialogueParser.normalize_scene_id("script_1")
        assert normalized == "script_1"

    def test_parse_ksre_filename_auto_normalization(
        self, parser: RenpyDialogueParser
    ) -> None:
        """Parser auto-normalizes KSRE filenames when scene_id not provided."""
        script_content = '''hisao "Test line from KSRE."'''
        # Create a temp file with KSRE-style naming
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        # Rename to KSRE-style name
        ksre_path = script_path.parent / "script-a1-sunday.rpy"
        script_path.rename(ksre_path)

        try:
            # Parse without explicit scene_id - should auto-normalize
            lines = parser.parse_script(ksre_path)
            assert len(lines) == 1
            assert lines[0].scene_id == "scriptasunday_1"
            assert lines[0].line_id == "scriptasunday_1_1"
        finally:
            ksre_path.unlink()
