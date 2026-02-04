"""Unsupported character check implementation."""

from __future__ import annotations

import re

from rentl_core.qa.protocol import DeterministicCheckResult
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import JsonValue, QaCategory, QaSeverity


class UnsupportedCharacterCheck:
    """Check for characters outside the allowed set.

    This check detects characters in translated lines that are not in
    the configured allowlist. Useful for ensuring compatibility with
    game engines that have limited character support.

    Parameters:
        allowed_ranges: List of Unicode range specifications (required).
            Formats: "U+0000-U+007F" (range), "U+0041" (single), or
            literal characters.
        allow_common_punctuation: Include common punctuation automatically
            (default: True).
    """

    check_name = "unsupported_characters"
    category = QaCategory.FORMATTING

    def __init__(self) -> None:
        """Initialize the check in unconfigured state."""
        self._allowed_codepoints: set[int] = set()
        self._configured: bool = False

    def configure(self, parameters: dict[str, JsonValue] | None) -> None:
        """Configure the check with allowed character ranges.

        Args:
            parameters: Must include allowed_ranges (list of strings).
                Optional allow_common_punctuation (bool, default True).

        Raises:
            ValueError: If allowed_ranges is missing or invalid.
        """
        if parameters is None:
            raise ValueError("unsupported_characters check requires allowed_ranges")

        allowed_ranges = parameters.get("allowed_ranges")
        if not isinstance(allowed_ranges, list) or not allowed_ranges:
            raise ValueError("allowed_ranges must be a non-empty list")

        self._allowed_codepoints = self._parse_ranges(allowed_ranges)

        # Optionally add common punctuation
        if parameters.get("allow_common_punctuation", True):
            common = " \n\t.,:;!?\"'()-/"
            for char in common:
                self._allowed_codepoints.add(ord(char))

        self._configured = True

    def _parse_ranges(self, ranges: list[JsonValue]) -> set[int]:
        """Parse Unicode range specifications.

        Args:
            ranges: List of range specifications.

        Returns:
            Set of allowed codepoints.

        Raises:
            ValueError: If any range specification is invalid.
        """
        codepoints: set[int] = set()

        for spec in ranges:
            if not isinstance(spec, str):
                raise ValueError(f"Range spec must be string: {spec}")

            # Handle range format: U+0000-U+007F
            range_match = re.match(r"^U\+([0-9A-Fa-f]+)-U\+([0-9A-Fa-f]+)$", spec)
            if range_match:
                start = int(range_match.group(1), 16)
                end = int(range_match.group(2), 16)
                if start > end:
                    raise ValueError(f"Invalid range (start > end): {spec}")
                codepoints.update(range(start, end + 1))
                continue

            # Handle single codepoint: U+0000
            single_match = re.match(r"^U\+([0-9A-Fa-f]+)$", spec)
            if single_match:
                codepoints.add(int(single_match.group(1), 16))
                continue

            # Treat as literal character(s)
            codepoints.update(ord(char) for char in spec)

        return codepoints

    def check_line(
        self,
        line: TranslatedLine,
        severity: QaSeverity,
    ) -> list[DeterministicCheckResult]:
        """Check for unsupported characters.

        Args:
            line: Translated line to check.
            severity: Severity for any issues found.

        Returns:
            List with one result if unsupported chars found, empty otherwise.

        Raises:
            ValueError: If check is not configured.
        """
        if not self._configured:
            raise ValueError("Check not configured")

        unsupported: list[tuple[int, str]] = []

        for index, char in enumerate(line.text):
            if ord(char) not in self._allowed_codepoints:
                unsupported.append((index, char))

        if not unsupported:
            return []

        # Group unsupported characters for reporting
        char_summary = ", ".join(
            f"'{char}' (U+{ord(char):04X}) at position {pos}"
            for pos, char in unsupported[:5]  # Limit to first 5
        )
        if len(unsupported) > 5:
            char_summary += f" and {len(unsupported) - 5} more"

        return [
            DeterministicCheckResult(
                line_id=line.line_id,
                category=self.category,
                severity=severity,
                message=f"Line contains unsupported characters: {char_summary}",
                suggestion="Replace unsupported characters with allowed alternatives",
                metadata={
                    "unsupported_count": len(unsupported),
                    "unsupported_chars": [
                        {
                            "position": pos,
                            "char": char,
                            "codepoint": f"U+{ord(char):04X}",
                        }
                        for pos, char in unsupported[:10]
                    ],
                },
            )
        ]
