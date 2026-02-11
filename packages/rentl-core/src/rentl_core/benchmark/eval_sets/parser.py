"""Ren'Py script parser for extracting dialogue into SourceLine format."""

import re
from pathlib import Path

from rentl_schemas.io import SourceLine


class RenpyDialogueParser:
    """Parses Ren'Py .rpy script files into SourceLine format."""

    # Ren'Py dialogue patterns (for original script files)
    DIALOGUE_WITH_SPEAKER = re.compile(
        r'^\s*(?P<speaker>\w+)\s+"(?P<text>(?:[^"\\]|\\.)*)"'
    )
    NARRATION = re.compile(r'^\s*"(?P<text>(?:[^"\\]|\\.)*)"')
    MENU_CHOICE = re.compile(r'^\s*"(?P<text>(?:[^"\\]|\\.)*)":')

    # Translation file patterns
    TRANSLATE_BLOCK = re.compile(r"^\s*translate\s+\w+\s+(?P<label>\w+):")
    TRANSLATE_STRINGS_BLOCK = re.compile(r"^\s*translate\s+\w+\s+strings:")
    ORIGINAL_COMMENT = re.compile(r'^\s*#\s+"(?P<text>(?:[^"\\]|\\.)*)"')
    OLD_STRING = re.compile(r'^\s*old\s+"(?P<text>(?:[^"\\]|\\.)*)"')
    NEW_STRING = re.compile(r'^\s*new\s+"(?P<text>(?:[^"\\]|\\.)*)"')
    TRANSLATED_SPEAKER = re.compile(
        r'^\s*(?P<speaker>\w+)\s+"(?P<text>(?:[^"\\]|\\.)*)"'
    )
    TRANSLATED_NARRATION = re.compile(r'^\s*"(?P<text>(?:[^"\\]|\\.)*)"')

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

        Supports both original script files and translation files.
        Translation files are detected by the presence of 'translate' blocks.

        Args:
            script_path: Path to the .rpy script file
            scene_id: Optional scene identifier (defaults to normalized script
                filename without extension)

        Returns:
            List of SourceLine records extracted from the script
        """
        if scene_id is None:
            scene_id = self.normalize_scene_id(script_path.stem)

        content = script_path.read_text(encoding="utf-8")
        content_lines = content.splitlines()

        # Detect if this is a translation file by checking for translate blocks
        is_translation_file = any(
            self.TRANSLATE_BLOCK.match(line) for line in content_lines[:50]
        )

        if is_translation_file:
            return self._parse_translation_file(content_lines, scene_id)
        else:
            return self._parse_original_script(content_lines, scene_id)

    def _parse_original_script(
        self, content_lines: list[str], scene_id: str
    ) -> list[SourceLine]:
        """Parse original Ren'Py script format.

        Returns:
            List of SourceLine records extracted from the script.
        """
        lines: list[SourceLine] = []

        for line_num, line in enumerate(content_lines, 1):
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

    def _parse_translation_file(
        self, content_lines: list[str], scene_id: str
    ) -> list[SourceLine]:
        """Parse Ren'Py translation file format.

        Translation files have blocks like:
            translate jp label_id:
                # "Original English text"
                speaker "Translated text"
        or:
            translate jp label_id:
                # "Original English text"
                "Translated text (narration)"
        or:
            translate jp strings:
                old "English source"
                new "Translated text"

        Returns:
            List of SourceLine records extracted from the translation file.
        """
        lines: list[SourceLine] = []
        i = 0

        while i < len(content_lines):
            line = content_lines[i]

            # Check for translate strings block (special handling for old/new pairs)
            strings_match = self.TRANSLATE_STRINGS_BLOCK.match(line)
            if strings_match:
                translate_line_num = i + 1
                i += 1

                # Parse old/new pairs within this strings block
                # Continue until we hit a non-indented line (next block)
                while i < len(content_lines):
                    current_line = content_lines[i]

                    # If we hit a non-indented line, we've left the strings block
                    if (
                        current_line
                        and not current_line.startswith((" ", "\t"))
                        and current_line.strip()
                    ):
                        break

                    # Skip blank lines
                    if not current_line.strip():
                        i += 1
                        continue

                    # Look for "old" line (skip it, just consume)
                    old_match = self.OLD_STRING.match(current_line)
                    if old_match:
                        i += 1
                        continue

                    # Look for "new" line (emit this as translated text)
                    new_match = self.NEW_STRING.match(current_line)
                    if new_match:
                        self.line_counter += 1
                        lines.append(
                            SourceLine(
                                line_id=f"{scene_id}_{self.line_counter}",
                                scene_id=scene_id,
                                # String translations are UI text, no speaker
                                speaker=None,
                                text=self._unescape_string(new_match.group("text")),
                                metadata={
                                    "source_line": translate_line_num,
                                    "type": "string",
                                },
                            )
                        )
                        i += 1
                        continue

                    # Skip any other content within the strings block
                    i += 1
                continue

            # Look for regular translate block start
            match = self.TRANSLATE_BLOCK.match(line)
            if match:
                translate_line_num = i + 1
                i += 1

                # Skip blank lines and comments until we find the translated text
                while i < len(content_lines):
                    current_line = content_lines[i]

                    # Skip comment lines (including original English text)
                    if current_line.strip().startswith("#"):
                        i += 1
                        continue

                    # Skip blank lines
                    if not current_line.strip():
                        i += 1
                        continue

                    # Found translated text - try to parse it
                    # IMPORTANT: Do not match "old" or "new" as speakers
                    # Check for old/new patterns first to reject them
                    if self.OLD_STRING.match(current_line) or self.NEW_STRING.match(
                        current_line
                    ):
                        i += 1
                        break

                    # Try dialogue with speaker first
                    speaker_match = self.TRANSLATED_SPEAKER.match(current_line)
                    if speaker_match:
                        self.line_counter += 1
                        lines.append(
                            SourceLine(
                                line_id=f"{scene_id}_{self.line_counter}",
                                scene_id=scene_id,
                                speaker=speaker_match.group("speaker"),
                                text=self._unescape_string(speaker_match.group("text")),
                                metadata={"source_line": translate_line_num},
                            )
                        )
                        i += 1
                        break

                    # Try narration (no speaker)
                    narration_match = self.TRANSLATED_NARRATION.match(current_line)
                    if narration_match:
                        self.line_counter += 1
                        lines.append(
                            SourceLine(
                                line_id=f"{scene_id}_{self.line_counter}",
                                scene_id=scene_id,
                                speaker=None,
                                text=self._unescape_string(
                                    narration_match.group("text")
                                ),
                                metadata={"source_line": translate_line_num},
                            )
                        )
                        i += 1
                        break

                    # If we hit a non-blank, non-comment line that doesn't match
                    # our patterns, skip this translate block
                    i += 1
                    break
            else:
                i += 1

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
