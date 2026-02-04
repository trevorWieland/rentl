"""Check for untranslated lines (text matches source_text)."""

from __future__ import annotations

from rentl_core.qa.protocol import DeterministicCheckResult
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import JsonValue, QaCategory, QaSeverity


class UntranslatedLineCheck:
    """Check for translated lines that match the source text."""

    check_name = "untranslated_line"
    category = QaCategory.OTHER

    def configure(self, parameters: dict[str, JsonValue] | None) -> None:
        """Configure the check.

        Args:
            parameters: Not used for this check.
        """

    def check_line(
        self,
        line: TranslatedLine,
        severity: QaSeverity,
    ) -> list[DeterministicCheckResult]:
        """Check if translated text matches the source text.

        Args:
            line: Translated line to check.
            severity: Severity for any issues found.

        Returns:
            List with one result if untranslated, empty otherwise.
        """
        if line.source_text is None:
            return []
        if line.text != line.source_text:
            return []
        return [
            DeterministicCheckResult(
                line_id=line.line_id,
                category=self.category,
                severity=severity,
                message="Translated line matches source text",
                suggestion="Translate the line into the target language",
                metadata=None,
            )
        ]
