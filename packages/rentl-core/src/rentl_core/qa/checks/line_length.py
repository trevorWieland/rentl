"""Line length check implementation."""

from __future__ import annotations

from rentl_core.qa.protocol import DeterministicCheckResult
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import JsonValue, QaCategory, QaSeverity


class LineLengthCheck:
    """Check for lines exceeding maximum length.

    This check detects translated lines that exceed a configured maximum
    length. Length can be measured in characters or bytes.

    Parameters:
        max_length: Maximum allowed line length (required).
        count_mode: How to count length - "characters" (default) or "bytes".
    """

    check_name = "line_length"
    category = QaCategory.FORMATTING

    def __init__(self) -> None:
        """Initialize the check in unconfigured state."""
        self._max_length: int | None = None
        self._count_mode: str = "characters"

    def configure(self, parameters: dict[str, JsonValue] | None) -> None:
        """Configure the check with parameters.

        Args:
            parameters: Must include max_length (positive int).
                Optional count_mode ("characters" or "bytes").

        Raises:
            ValueError: If max_length is missing or invalid.
        """
        if parameters is None:
            raise ValueError("line_length check requires max_length parameter")

        max_length = parameters.get("max_length")
        if max_length is None:
            raise ValueError("line_length check requires max_length parameter")
        if not isinstance(max_length, int) or max_length <= 0:
            raise ValueError("max_length must be a positive integer")
        self._max_length = max_length

        count_mode = parameters.get("count_mode", "characters")
        if count_mode not in {"characters", "bytes"}:
            raise ValueError("count_mode must be 'characters' or 'bytes'")
        self._count_mode = str(count_mode)

    def check_line(
        self,
        line: TranslatedLine,
        severity: QaSeverity,
    ) -> list[DeterministicCheckResult]:
        """Check if line exceeds maximum length.

        Args:
            line: Translated line to check.
            severity: Severity for any issues found.

        Returns:
            List with one result if line exceeds limit, empty otherwise.

        Raises:
            ValueError: If check is not configured.
        """
        if self._max_length is None:
            raise ValueError("Check not configured")

        text = line.text
        if self._count_mode == "characters":
            length = len(text)
        else:
            length = len(text.encode("utf-8"))

        if length <= self._max_length:
            return []

        return [
            DeterministicCheckResult(
                line_id=line.line_id,
                category=self.category,
                severity=severity,
                message=(
                    f"Line exceeds maximum length "
                    f"({length} > {self._max_length} {self._count_mode})"
                ),
                suggestion=(
                    f"Shorten line to {self._max_length} {self._count_mode} or less"
                ),
                metadata={
                    "actual_length": length,
                    "max_length": self._max_length,
                    "count_mode": self._count_mode,
                },
            )
        ]
