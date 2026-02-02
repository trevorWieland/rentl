"""Unit tests for deterministic QA runner.

Note: Some checks (empty_translation, whitespace) cannot find issues
with validated TranslatedLine objects due to schema constraints.
"""

import pytest

from rentl_core.qa.runner import DeterministicQaRunner
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import QaCategory, QaSeverity


def _make_line(text: str, line_id: str = "line_1") -> TranslatedLine:
    return TranslatedLine(line_id=line_id, text=text)


class TestDeterministicQaRunner:
    """Tests for DeterministicQaRunner."""

    def test_empty_runner_produces_no_issues(self) -> None:
        """Runner with no checks produces no issues."""
        runner = DeterministicQaRunner()
        lines = [_make_line("Hello World")]
        issues = runner.run_checks(lines)
        assert issues == []

    def test_configure_unknown_check_raises(self) -> None:
        """Configuring unknown check raises."""
        runner = DeterministicQaRunner()
        with pytest.raises(ValueError, match="Unknown check"):
            runner.configure_check("nonexistent", QaSeverity.MAJOR)

    def test_configure_invalid_parameters_raises(self) -> None:
        """Configuring check with invalid parameters raises."""
        runner = DeterministicQaRunner()
        with pytest.raises(ValueError, match="max_length"):
            runner.configure_check("line_length", QaSeverity.MAJOR, {})

    def test_single_check_execution(self) -> None:
        """Single check runs and produces issues."""
        runner = DeterministicQaRunner()
        runner.configure_check(
            "line_length",
            QaSeverity.MAJOR,
            {"max_length": 5},
        )

        lines = [_make_line("Hello World", line_id="line_1")]
        issues = runner.run_checks(lines)

        assert len(issues) == 1
        assert issues[0].line_id == "line_1"
        assert issues[0].category == QaCategory.FORMATTING
        assert issues[0].severity == QaSeverity.MAJOR

    def test_multiple_checks_execution(self) -> None:
        """Multiple checks all run on each line."""
        runner = DeterministicQaRunner()
        runner.configure_check(
            "line_length",
            QaSeverity.MAJOR,
            {"max_length": 5},
        )
        # Note: empty_translation won't find issues due to schema constraints
        runner.configure_check("empty_translation", QaSeverity.CRITICAL)

        # Line that triggers line_length only (too long)
        lines = [_make_line("Hello World", line_id="line_1")]
        issues = runner.run_checks(lines)

        # Should have line_length issue only
        assert len(issues) == 1
        assert issues[0].severity == QaSeverity.MAJOR

    def test_multiple_lines(self) -> None:
        """Runner processes all lines."""
        runner = DeterministicQaRunner()
        runner.configure_check(
            "line_length",
            QaSeverity.MAJOR,
            {"max_length": 5},
        )

        lines = [
            _make_line("Hi", line_id="line_1"),  # OK
            _make_line("Hello World", line_id="line_2"),  # Too long
            _make_line("OK", line_id="line_3"),  # OK
            _make_line("This is too long", line_id="line_4"),  # Too long
        ]
        issues = runner.run_checks(lines)

        assert len(issues) == 2
        line_ids = {issue.line_id for issue in issues}
        assert line_ids == {"line_2", "line_4"}

    def test_issues_have_valid_issue_ids(self) -> None:
        """Generated issues have valid UUIDv7 issue IDs."""
        runner = DeterministicQaRunner()
        runner.configure_check(
            "line_length",
            QaSeverity.MAJOR,
            {"max_length": 5},
        )

        lines = [_make_line("Hello World")]
        issues = runner.run_checks(lines)

        assert len(issues) == 1
        # issue_id should be a valid UUID
        assert issues[0].issue_id is not None
        assert issues[0].issue_id.version == 7

    def test_empty_lines_list(self) -> None:
        """Runner handles empty lines list."""
        runner = DeterministicQaRunner()
        runner.configure_check(
            "line_length",
            QaSeverity.MAJOR,
            {"max_length": 5},
        )

        issues = runner.run_checks([])
        assert issues == []

    def test_check_severity_independent(self) -> None:
        """Each check can have different severity."""
        runner = DeterministicQaRunner()
        runner.configure_check(
            "line_length",
            QaSeverity.CRITICAL,
            {"max_length": 5},
        )
        runner.configure_check(
            "unsupported_characters",
            QaSeverity.INFO,
            {"allowed_ranges": ["U+0000-U+007F"]},
        )

        lines = [
            _make_line("Hello World", line_id="line_1"),  # Too long
            _make_line("日本語", line_id="line_2"),  # Unsupported chars
        ]
        issues = runner.run_checks(lines)

        # line_1 should have CRITICAL (line length)
        # line_2 should have INFO (unsupported chars)
        line_1_issues = [i for i in issues if i.line_id == "line_1"]
        line_2_issues = [i for i in issues if i.line_id == "line_2"]

        assert len(line_1_issues) == 1
        assert line_1_issues[0].severity == QaSeverity.CRITICAL

        assert len(line_2_issues) == 1
        assert line_2_issues[0].severity == QaSeverity.INFO
