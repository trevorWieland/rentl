"""Ren'Py script parser for extracting dialogue into SourceLine format."""

import re
from pathlib import Path

from rentl_schemas.io import SourceLine


class RenpyDialogueParser:
    """Parses Ren'Py .rpy script files into SourceLine format."""

    # Ren'Py dialogue patterns
    DIALOGUE_WITH_SPEAKER = re.compile(
        r'^\s*(?P<speaker>\w+)\s+"(?P<text>(?:[^"\\]|\\.)*)"'
    )
    NARRATION = re.compile(r'^\s*"(?P<text>(?:[^"\\]|\\.)*)"')
    MENU_CHOICE = re.compile(r'^\s*"(?P<text>(?:[^"\\]|\\.)*)":')

    def __init__(self) -> None:
        """Initialize the parser."""
        self.line_counter = 0

    @staticmethod
    def normalize_scene_id(filename_stem: str) -> str:
        """Normalize a filename stem to match HumanReadableId pattern.

        The HumanReadableId pattern requires: ^[a-z]+(?:_[0-9]+)+$
        (letters, then one or more groups of underscore+digits)

        This function extracts alphanumeric components, then constructs
        a valid ID by using lowercase letters as the base, followed by
        numeric components as underscore-separated suffixes.

        Args:
            filename_stem: Filename without extension (e.g., "script-a1-sunday")

        Returns:
            Normalized ID matching HumanReadableId pattern (e.g., "scripta_1_sunday_0")

        Examples:
            >>> RenpyDialogueParser.normalize_scene_id("script-a1-sunday")
            'scripta_1_sunday_0'
            >>> RenpyDialogueParser.normalize_scene_id("test")
            'test_0'
        """
        # Lowercase and split by non-alphanumeric characters
        stem = filename_stem.lower()
        # Replace any non-alphanumeric with space and split
        parts = re.split(r"[^a-z0-9]+", stem)
        parts = [p for p in parts if p]  # Remove empty strings

        # Separate letters and numbers, build pattern: letters_num1_num2...
        letter_parts: list[str] = []
        number_parts: list[str] = []

        for part in parts:
            # Extract digits from this part
            digits = "".join(c for c in part if c.isdigit())
            letters = "".join(c for c in part if c.isalpha())

            if letters:
                letter_parts.append(letters)
            if digits:
                number_parts.append(digits)

        # Build: concatenate all letters, then add _number for each number part
        if not letter_parts:
            # Edge case: no letters at all (shouldn't happen for filenames)
            letter_parts = ["scene"]

        base = "".join(letter_parts)

        # Ensure at least one numeric suffix
        if not number_parts:
            number_parts = ["0"]

        # Build final ID: base_num1_num2_...
        scene_id = base + "".join(f"_{num}" for num in number_parts)

        return scene_id

    def parse_script(
        self,
        script_path: Path,
        scene_id: str | None = None,
    ) -> list[SourceLine]:
        """Parse a Ren'Py script file into SourceLine records.

        Args:
            script_path: Path to the .rpy script file
            scene_id: Optional scene identifier (defaults to normalized script
                filename without extension)

        Returns:
            List of SourceLine records extracted from the script
        """
        if scene_id is None:
            scene_id = self.normalize_scene_id(script_path.stem)

        lines: list[SourceLine] = []
        content = script_path.read_text(encoding="utf-8")

        for line_num, line in enumerate(content.splitlines(), 1):
            # Try to match dialogue with speaker
            match = self.DIALOGUE_WITH_SPEAKER.match(line)
            if match:
                self.line_counter += 1
                lines.append(
                    SourceLine(
                        line_id=f"{scene_id}_{self.line_counter}",
                        scene_id=scene_id,
                        speaker=match.group("speaker"),
                        text=self._unescape_string(match.group("text")),
                        metadata={"source_line": line_num},
                    )
                )
                continue

            # Try to match menu choice (before narration, as they both start
            # with quotes)
            match = self.MENU_CHOICE.match(line)
            if match:
                self.line_counter += 1
                lines.append(
                    SourceLine(
                        line_id=f"{scene_id}_{self.line_counter}",
                        scene_id=scene_id,
                        speaker="[menu]",
                        text=self._unescape_string(match.group("text")),
                        metadata={"source_line": line_num, "type": "choice"},
                    )
                )
                continue

            # Try to match narration (no speaker)
            match = self.NARRATION.match(line)
            if match:
                self.line_counter += 1
                lines.append(
                    SourceLine(
                        line_id=f"{scene_id}_{self.line_counter}",
                        scene_id=scene_id,
                        speaker=None,
                        text=self._unescape_string(match.group("text")),
                        metadata={"source_line": line_num},
                    )
                )
                continue

        return lines

    def _unescape_string(self, text: str) -> str:
        """Unescape Ren'Py string escape sequences.

        Args:
            text: String with escape sequences

        Returns:
            Unescaped string
        """
        # Handle common escape sequences
        text = text.replace('\\"', '"')
        text = text.replace("\\n", "\n")
        text = text.replace("\\t", "\t")
        text = text.replace("\\\\", "\\")
        return text
