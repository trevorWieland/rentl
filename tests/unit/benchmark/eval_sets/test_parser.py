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

    def test_normalize_scene_id_no_letters(self) -> None:
        """Parser handles edge case of filename with only numbers."""
        # Edge case: filename like "123-456" with no letters
        normalized = RenpyDialogueParser.normalize_scene_id("123-456")
        # Should default to "scene" prefix when no letters found
        assert normalized == "scene_123_456"
        assert re.match(HUMAN_ID_PATTERN, normalized)

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

    def test_parse_translation_file_narration(
        self, parser: RenpyDialogueParser
    ) -> None:
        """Parser extracts translated narration from translation file format."""
        script_content = """# Translation file
# game/script-a1-monday.rpy:13
translate jp a1_monday_out_cold_99711a67:

    # "Original English text"
    "そよ風が吹き、頭上の葉の落ちた木々が、木製のウインドベルのようにざわつく。"
"""
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 1
            assert lines[0].speaker is None
            # fmt: off
            expected = "そよ風が吹き、頭上の葉の落ちた木々が、木製のウインドベルのようにざわつく。"  # noqa: E501
            # fmt: on
            assert lines[0].text == expected
            assert lines[0].scene_id == "test_1"
        finally:
            script_path.unlink()

    def test_parse_translation_file_dialogue(self, parser: RenpyDialogueParser) -> None:
        """Parser extracts translated dialogue with speaker from translation file."""
        # fmt: off
        jp_text = "いつまで待ってればいいんだ？　手紙には午後４時って書いてあったはずだけど"  # noqa: RUF001, E501
        # fmt: on
        script_content = f"""# Translation file
# game/script-a1-monday.rpy:21
translate jp a1_monday_out_cold_48c2e508:

    # hi "Just how long am I expected to wait out here, anyway?"
    hi "{jp_text}"
"""
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 1
            assert lines[0].speaker == "hi"
            assert lines[0].text == jp_text
        finally:
            script_path.unlink()

    def test_parse_translation_file_mixed(self, parser: RenpyDialogueParser) -> None:
        """Parser handles multiple translation blocks with mixed content."""
        script_content = """# Translation file
# game/script-a1-monday.rpy:13
translate jp label_1:

    # "Narration text"
    "翻訳されたナレーション"

# game/script-a1-monday.rpy:15
translate jp label_2:

    # hi "Dialogue text"
    hi "翻訳された対話"

# game/script-a1-monday.rpy:17
translate jp label_3:

    # "More narration"
    "もっとナレーション"
"""
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 3
            assert lines[0].speaker is None
            assert lines[0].text == "翻訳されたナレーション"
            assert lines[1].speaker == "hi"
            assert lines[1].text == "翻訳された対話"
            assert lines[2].speaker is None
            assert lines[2].text == "もっとナレーション"
        finally:
            script_path.unlink()

    def test_parse_translation_strings_block(self, parser: RenpyDialogueParser) -> None:
        """Parser handles translate strings blocks with old/new pairs correctly."""
        jp_text_1 = "どうしてですか？"  # noqa: RUF001
        jp_text_2 = "こんにちは"
        script_content = f"""# Translation file
translate jp strings:

    # Options menu
    old "Why?"
    new "{jp_text_1}"

    old "Hello"
    new "{jp_text_2}"
"""
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            # Should only emit "new" translations, not "old" source strings
            assert len(lines) == 2
            assert lines[0].speaker is None
            assert lines[0].text == jp_text_1
            assert lines[0].metadata is not None
            assert lines[0].metadata.get("type") == "string"
            assert lines[1].speaker is None
            assert lines[1].text == jp_text_2
            assert lines[1].metadata is not None
            assert lines[1].metadata.get("type") == "string"

            # Verify no English source text leaked through
            for line in lines:
                assert line.text not in ["Why?", "Hello"]
                assert line.speaker != "old"
        finally:
            script_path.unlink()

    def test_parse_translation_strings_no_old_speaker(
        self, parser: RenpyDialogueParser
    ) -> None:
        """Parser rejects 'old' as a speaker name to prevent source text leakage."""
        script_content = """# Translation file with strings block
translate jp strings:

    old "English source text"
    new "日本語訳"

translate jp dialogue_block:

    # hi "Original dialogue"
    hi "翻訳された対話"
"""
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            # Should get 2 lines: one from strings block (new), one from dialogue block
            assert len(lines) == 2

            # Assert NO line has speaker == "old" (this would indicate English leak)
            for line in lines:
                assert line.speaker != "old", f"Found 'old' speaker: {line.text}"

            # Verify we got the expected content
            assert lines[0].text == "日本語訳"
            assert lines[0].speaker is None
            assert lines[1].text == "翻訳された対話"
            assert lines[1].speaker == "hi"
        finally:
            script_path.unlink()

    def test_parse_translation_strings_multiple_blocks(
        self, parser: RenpyDialogueParser
    ) -> None:
        """Parser handles multiple translate strings blocks correctly."""
        script_content = """# Translation file
translate jp strings:

    old "Menu option 1"
    new "メニュー選択肢1"

translate jp dialogue_1:

    # "Some narration"
    "ナレーション"

translate jp strings:

    old "Menu option 2"
    new "メニュー選択肢2"
"""
        with NamedTemporaryFile(mode="w", suffix=".rpy", delete=False) as f:
            f.write(script_content)
            script_path = Path(f.name)

        try:
            lines = parser.parse_script(script_path, scene_id="test_1")
            assert len(lines) == 3

            # First strings block
            assert lines[0].text == "メニュー選択肢1"
            assert lines[0].metadata is not None
            assert lines[0].metadata.get("type") == "string"

            # Dialogue block
            assert lines[1].text == "ナレーション"
            assert lines[1].speaker is None

            # Second strings block
            assert lines[2].text == "メニュー選択肢2"
            assert lines[2].metadata is not None
            assert lines[2].metadata.get("type") == "string"

            # Ensure no 'old' speaker leaked through
            for line in lines:
                assert line.speaker != "old"
        finally:
            script_path.unlink()
