"""Whitespace issues check implementation."""

from __future__ import annotations

from rentl_core.qa.protocol import DeterministicCheckResult
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import JsonValue, QaCategory, QaSeverity


class WhitespaceCheck:
    """Check for leading/trailing whitespace issues.

    This check detects translated lines that have unexpected leading or
    trailing whitespace. Generates separate issues for each type.

    Parameters:
        None required.
    """

    check_name = "whitespace"
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
        """Check for leading/trailing whitespace.

        Args:
            line: Translated line to check.
            severity: Severity for any issues found.

        Returns:
            List of results for each whitespace issue found.
        """
        results: list[DeterministicCheckResult] = []
        text = line.text

        has_leading = text != text.lstrip()
        has_trailing = text != text.rstrip()

        if has_leading:
            leading_ws = text[: len(text) - len(text.lstrip())]
            results.append(
                DeterministicCheckResult(
                    line_id=line.line_id,
                    category=self.category,
                    severity=severity,
                    message="Line has leading whitespace",
                    suggestion="Remove leading whitespace",
                    metadata={"leading_whitespace": repr(leading_ws)},
                )
            )

        if has_trailing:
            trailing_ws = text[len(text.rstrip()) :]
            results.append(
                DeterministicCheckResult(
                    line_id=line.line_id,
                    category=self.category,
                    severity=severity,
                    message="Line has trailing whitespace",
                    suggestion="Remove trailing whitespace",
                    metadata={"trailing_whitespace": repr(trailing_ws)},
                )
            )

        return results
