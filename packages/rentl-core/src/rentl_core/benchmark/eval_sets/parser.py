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

    def parse_script(
        self,
        script_path: Path,
        scene_id: str | None = None,
    ) -> list[SourceLine]:
        """Parse a Ren'Py script file into SourceLine records.

        Args:
            script_path: Path to the .rpy script file
            scene_id: Optional scene identifier (defaults to script filename
                without extension)

        Returns:
            List of SourceLine records extracted from the script
        """
        if scene_id is None:
            scene_id = script_path.stem

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
