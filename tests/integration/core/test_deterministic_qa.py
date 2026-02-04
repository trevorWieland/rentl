"""Integration tests for deterministic QA checks.

These tests verify the full flow of deterministic QA check execution,
from configuration through runner execution to issue generation.

Note: TranslatedLine schema has constraints (min_length=1, str_strip_whitespace)
that prevent empty and whitespace-only lines. Tests focus on checks that
can find issues with validated TranslatedLine objects.
"""

import pytest

from rentl_core.qa.runner import DeterministicQaRunner
from rentl_schemas.config import DeterministicQaCheckConfig, DeterministicQaConfig
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import QaCategory, QaSeverity

# Apply integration marker
pytestmark = pytest.mark.integration


def _make_line(line_id: str, text: str) -> TranslatedLine:
    return TranslatedLine(line_id=line_id, text=text)


class TestDeterministicQaIntegration:
    """Integration tests for deterministic QA flow."""

    def test_given_lines_with_issues_when_running_qa_then_issues_detected(
        self,
    ) -> None:
        """Given: Translated lines with formatting issues.

        When: Running deterministic QA checks.
        Then: All issues are detected and included in output.
        """
        # Given: Lines with various issues (only issues that can exist with schema)
        lines = [
            _make_line("line_1", "Hello World"),  # Clean, short
            _make_line("line_2", "This line is too long for the limit"),  # Too long
            _make_line(
                "line_3", "日本語テスト"
            ),  # Has unsupported chars (if ASCII only)
        ]

        # And: Configured runner
        runner = DeterministicQaRunner()
        runner.configure_check("line_length", QaSeverity.MAJOR, {"max_length": 20})
        runner.configure_check(
            "unsupported_characters",
            QaSeverity.CRITICAL,
            {"allowed_ranges": ["U+0000-U+007F"]},
        )

        # When: Running checks
        issues = runner.run_checks(lines)

        # Then: Issues detected for problematic lines
        line_ids_with_issues = {issue.line_id for issue in issues}
        assert "line_1" not in line_ids_with_issues  # Clean line
        assert "line_2" in line_ids_with_issues  # Too long
        assert "line_3" in line_ids_with_issues  # Unsupported chars

    def test_given_no_issues_when_running_qa_then_empty_output(self) -> None:
        """Given: Clean translated lines.

        When: Running deterministic QA checks.
        Then: No issues in output.
        """
        # Given: Clean lines
        lines = [
            _make_line("line_1", "Hello"),
            _make_line("line_2", "World"),
            _make_line("line_3", "Test"),
        ]

        # And: Configured runner
        runner = DeterministicQaRunner()
        runner.configure_check("line_length", QaSeverity.MAJOR, {"max_length": 100})
        runner.configure_check(
            "unsupported_characters",
            QaSeverity.CRITICAL,
            {"allowed_ranges": ["U+0000-U+007F"]},
        )

        # When: Running checks
        issues = runner.run_checks(lines)

        # Then: No issues
        assert issues == []

    def test_given_config_when_building_runner_then_checks_configured(self) -> None:
        """Given: DeterministicQaConfig with check configurations.

        When: Building a runner from config.
        Then: Runner executes configured checks.
        """
        # Given: Configuration
        config = DeterministicQaConfig(
            enabled=True,
            checks=[
                DeterministicQaCheckConfig(
                    check_name="line_length",
                    enabled=True,
                    severity=QaSeverity.MAJOR,
                    parameters={"max_length": 10},
                ),
                DeterministicQaCheckConfig(
                    check_name="unsupported_characters",
                    enabled=False,  # Disabled
                    severity=QaSeverity.CRITICAL,
                    parameters={"allowed_ranges": ["U+0000-U+007F"]},
                ),
            ],
        )

        # And: Test lines
        lines = [
            _make_line("line_1", "This is too long"),  # Line length issue
            _make_line("line_2", "Short"),  # OK
            _make_line("line_3", "日本語"),  # Would be unsupported if enabled
        ]

        # When: Building runner from config and running
        runner = DeterministicQaRunner()
        for check_config in config.checks:
            if check_config.enabled:
                runner.configure_check(
                    check_config.check_name,
                    check_config.severity,
                    check_config.parameters,
                )

        issues = runner.run_checks(lines)

        # Then: Only enabled checks produce issues
        line_ids = {issue.line_id for issue in issues}
        assert "line_1" in line_ids  # Line length (enabled)
        assert "line_2" not in line_ids  # OK
        assert "line_3" not in line_ids  # Unsupported check disabled

        # And: Severities match config
        line_1_issue = next(i for i in issues if i.line_id == "line_1")
        assert line_1_issue.severity == QaSeverity.MAJOR

    def test_given_unsupported_chars_when_running_qa_then_chars_detected(self) -> None:
        """Given: Lines with characters outside allowed ranges.

        When: Running unsupported character check.
        Then: Unsupported characters detected with details.
        """
        # Given: Lines with Japanese characters (outside ASCII)
        lines = [
            _make_line("line_1", "Hello World"),  # ASCII only
            _make_line("line_2", "こんにちは"),  # Japanese
            _make_line("line_3", "Hello 世界"),  # Mixed
        ]

        # And: ASCII-only configuration
        runner = DeterministicQaRunner()
        runner.configure_check(
            "unsupported_characters",
            QaSeverity.CRITICAL,
            {
                "allowed_ranges": ["U+0000-U+007F"],  # ASCII only
                "allow_common_punctuation": True,
            },
        )

        # When: Running checks
        issues = runner.run_checks(lines)

        # Then: Non-ASCII lines flagged
        line_ids = {issue.line_id for issue in issues}
        assert "line_1" not in line_ids  # ASCII only
        assert "line_2" in line_ids  # Japanese
        assert "line_3" in line_ids  # Mixed

        # And: Metadata includes character details
        line_2_issue = next(i for i in issues if i.line_id == "line_2")
        assert line_2_issue.metadata is not None
        assert line_2_issue.metadata["unsupported_count"] == 5  # 5 Japanese chars

    def test_issues_have_correct_category_and_structure(self) -> None:
        """Given: Various formatting issues.

        When: Running QA checks.
        Then: Issues have correct categories and structure.
        """
        # Given: Lines with issues
        lines = [
            _make_line("line_1", "This line exceeds the maximum allowed length"),
            _make_line("line_2", "日本語"),  # Unsupported chars
        ]

        runner = DeterministicQaRunner()
        runner.configure_check("line_length", QaSeverity.MAJOR, {"max_length": 20})
        runner.configure_check(
            "unsupported_characters",
            QaSeverity.CRITICAL,
            {"allowed_ranges": ["U+0000-U+007F"]},
        )

        # When: Running checks
        issues = runner.run_checks(lines)

        # Then: All issues are FORMATTING category
        for issue in issues:
            assert issue.category == QaCategory.FORMATTING

        # And: Issues have valid structure
        for issue in issues:
            assert issue.issue_id is not None
            assert issue.line_id is not None
            assert issue.message is not None
            assert len(issue.message) > 0
