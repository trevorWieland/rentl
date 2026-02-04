"""Deterministic QA check runner."""

from __future__ import annotations

from uuid import uuid7

from rentl_core.qa.protocol import DeterministicCheck, DeterministicCheckResult
from rentl_core.qa.registry import CheckRegistry, get_default_registry
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import JsonValue, QaSeverity
from rentl_schemas.qa import QaIssue


class DeterministicQaRunner:
    """Runner for deterministic QA checks.

    The runner manages a collection of configured checks and executes
    them against translated lines, producing QaIssue instances that
    can be merged into the QA phase output.
    """

    def __init__(
        self,
        registry: CheckRegistry | None = None,
    ) -> None:
        """Initialize the runner.

        Args:
            registry: Check registry to use. If None, uses the default
                registry with all built-in checks.
        """
        self._registry = registry or get_default_registry()
        self._checks: list[tuple[DeterministicCheck, QaSeverity]] = []

    def configure_check(
        self,
        check_name: str,
        severity: QaSeverity | str,
        parameters: dict[str, JsonValue] | None = None,
    ) -> None:
        """Configure and add a check to the runner.

        Args:
            check_name: Name of the check to add.
            severity: Severity for issues from this check (enum or string).
            parameters: Check-specific parameters.
        """
        check = self._registry.create(check_name)
        check.configure(parameters)
        # Ensure severity is enum (config may return string due to use_enum_values)
        if isinstance(severity, str):
            severity = QaSeverity(severity)
        self._checks.append((check, severity))

    def run_checks(
        self,
        translated_lines: list[TranslatedLine],
    ) -> list[QaIssue]:
        """Run all configured checks on translated lines.

        Args:
            translated_lines: Lines to check.

        Returns:
            List of QA issues found.
        """
        issues: list[QaIssue] = []

        for line in translated_lines:
            for check, severity in self._checks:
                results = check.check_line(line, severity)
                for result in results:
                    issue = self._result_to_issue(result)
                    issues.append(issue)

        return issues

    def _result_to_issue(self, result: DeterministicCheckResult) -> QaIssue:
        """Convert check result to QaIssue.

        Args:
            result: Check result to convert.

        Returns:
            QaIssue instance.
        """
        return QaIssue(
            issue_id=uuid7(),
            line_id=result.line_id,
            category=result.category,
            severity=result.severity,
            message=result.message,
            suggestion=result.suggestion,
            metadata=result.metadata,
        )
