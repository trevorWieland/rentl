"""Protocol and result types for deterministic QA checks."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import (
    JsonValue,
    LineId,
    QaCategory,
    QaSeverity,
)


class DeterministicCheckResult(BaseModel):
    """Result of a single check on a single line.

    Attributes:
        line_id: Identifier of the checked line.
        category: QA category for this issue.
        severity: Severity level for this issue.
        message: Human-readable description of the issue.
        suggestion: Optional suggestion for fixing the issue.
        metadata: Optional structured metadata about the issue.
    """

    model_config = ConfigDict(frozen=True)

    line_id: LineId = Field(description="Identifier of the checked line")
    category: QaCategory = Field(description="QA category for this issue")
    severity: QaSeverity = Field(description="Severity level for this issue")
    message: str = Field(description="Human-readable description of the issue")
    suggestion: str | None = Field(
        default=None, description="Optional suggestion for fixing the issue"
    )
    metadata: dict[str, JsonValue] | None = Field(
        default=None, description="Optional structured metadata about the issue"
    )


@runtime_checkable
class DeterministicCheck(Protocol):
    """Protocol for deterministic QA checks.

    Deterministic checks identify issues that can be detected without
    LLM reasoning, such as line length violations, invalid characters,
    empty translations, and whitespace issues.
    """

    @property
    def check_name(self) -> str:
        """Unique identifier for this check."""
        ...

    @property
    def category(self) -> QaCategory:
        """QA category for issues from this check."""
        ...

    def configure(self, parameters: dict[str, JsonValue] | None) -> None:
        """Configure the check with parameters from config.

        Args:
            parameters: Check-specific parameters.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        ...

    def check_line(
        self,
        line: TranslatedLine,
        severity: QaSeverity,
    ) -> list[DeterministicCheckResult]:
        """Run check on a single translated line.

        Args:
            line: Translated line to check.
            severity: Configured severity for issues.

        Returns:
            List of check results (empty if line passes).
        """
        ...
