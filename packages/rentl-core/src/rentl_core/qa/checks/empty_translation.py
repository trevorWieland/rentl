"""Empty translation check implementation."""

from __future__ import annotations

from rentl_core.qa.protocol import DeterministicCheckResult
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import JsonValue, QaCategory, QaSeverity


class EmptyTranslationCheck:
    """Check for empty translated lines.

    This check detects translated lines that are empty or contain only
    whitespace. Such lines typically indicate incomplete translation.

    Parameters:
        None required.
    """

    check_name = "empty_translation"
    category = QaCategory.FORMATTING

    def configure(self, parameters: dict[str, JsonValue] | None) -> None:
        """Configure the check.

        Args:
            parameters: Not used for this check.
        """
        # No configuration needed

    def check_line(
        self,
        line: TranslatedLine,
        severity: QaSeverity,
    ) -> list[DeterministicCheckResult]:
        """Check if line is empty or whitespace-only.

        Args:
            line: Translated line to check.
            severity: Severity for any issues found.

        Returns:
            List with one result if line is empty, empty otherwise.
        """
        text = line.text.strip()

        if text:
            return []

        return [
            DeterministicCheckResult(
                line_id=line.line_id,
                category=self.category,
                severity=severity,
                message="Translated line is empty or contains only whitespace",
                suggestion="Provide a translation for this line",
                metadata=None,
            )
        ]
