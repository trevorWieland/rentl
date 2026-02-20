"""BDD integration tests for deterministic QA checks.

These tests verify the full flow of deterministic QA check execution,
from configuration through runner execution to issue generation.

Note: TranslatedLine schema has constraints (min_length=1, str_strip_whitespace)
that prevent empty and whitespace-only lines. Tests focus on checks that
can find issues with validated TranslatedLine objects.
"""

from pytest_bdd import given, scenarios, then, when

from rentl_core.qa.runner import DeterministicQaRunner
from rentl_schemas.config import DeterministicQaCheckConfig, DeterministicQaConfig
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import QaCategory, QaSeverity

# Link feature file
scenarios("../features/core/deterministic_qa.feature")


def _make_line(line_id: str, text: str) -> TranslatedLine:
    return TranslatedLine(line_id=line_id, text=text)


class QaContext:
    """Context object for QA BDD scenarios."""

    lines: list[TranslatedLine] | None = None
    runner: DeterministicQaRunner | None = None
    issues: list | None = None
    config: DeterministicQaConfig | None = None


@given("translated lines with formatting issues", target_fixture="ctx")
def given_lines_with_issues() -> QaContext:
    """Set up translated lines that contain formatting issues.

    Returns:
        QaContext with fields initialized.
    """
    ctx = QaContext()
    ctx.lines = [
        _make_line("line_1", "Hello World"),  # Clean, short
        _make_line("line_2", "This line is too long for the limit"),  # Too long
        _make_line("line_3", "日本語テスト"),  # Has unsupported chars (if ASCII only)
    ]
    return ctx


@given("clean translated lines", target_fixture="ctx")
def given_clean_lines() -> QaContext:
    """Set up translated lines with no formatting issues.

    Returns:
        QaContext with fields initialized.
    """
    ctx = QaContext()
    ctx.lines = [
        _make_line("line_1", "Hello"),
        _make_line("line_2", "World"),
        _make_line("line_3", "Test"),
    ]
    return ctx


@given(
    "a DeterministicQaConfig with one enabled and one disabled check",
    target_fixture="ctx",
)
def given_config_with_enabled_and_disabled() -> QaContext:
    """Set up a QA config with one enabled and one disabled check.

    Returns:
        QaContext with fields initialized.
    """
    ctx = QaContext()
    ctx.config = DeterministicQaConfig(
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
                enabled=False,
                severity=QaSeverity.CRITICAL,
                parameters={"allowed_ranges": ["U+0000-U+007F"]},
            ),
        ],
    )
    return ctx


@given("translated lines with characters outside ASCII range", target_fixture="ctx")
def given_lines_outside_ascii() -> QaContext:
    """Set up translated lines containing non-ASCII characters.

    Returns:
        QaContext with fields initialized.
    """
    ctx = QaContext()
    ctx.lines = [
        _make_line("line_1", "Hello World"),  # ASCII only
        _make_line("line_2", "こんにちは"),  # Japanese
        _make_line("line_3", "Hello 世界"),  # Mixed
    ]
    return ctx


@given("translated lines with various formatting issues", target_fixture="ctx")
def given_lines_with_various_issues() -> QaContext:
    """Set up translated lines with multiple types of formatting issues.

    Returns:
        QaContext with fields initialized.
    """
    ctx = QaContext()
    ctx.lines = [
        _make_line("line_1", "This line exceeds the maximum allowed length"),
        _make_line("line_2", "日本語"),  # Unsupported chars
    ]
    return ctx


@given("a QA runner configured for line length and unsupported characters")
def given_runner_line_length_and_unsupported(ctx: QaContext) -> None:
    """Configure a QA runner with line length and unsupported character checks."""
    ctx.runner = DeterministicQaRunner()
    # Use max_length=20 for the issues scenario, 100 for clean
    max_length = (
        100 if ctx.lines and all(len(line.text) < 30 for line in ctx.lines) else 20
    )
    ctx.runner.configure_check(
        "line_length", QaSeverity.MAJOR, {"max_length": max_length}
    )
    ctx.runner.configure_check(
        "unsupported_characters",
        QaSeverity.CRITICAL,
        {"allowed_ranges": ["U+0000-U+007F"]},
    )


@given("translated lines with issues for both checks")
def given_lines_for_both_checks(ctx: QaContext) -> None:
    """Set up translated lines with issues detectable by both configured checks."""
    ctx.lines = [
        _make_line("line_1", "This is too long"),  # Line length issue
        _make_line("line_2", "Short"),  # OK
        _make_line("line_3", "日本語"),  # Would be unsupported if enabled
    ]


@given("a QA runner configured for ASCII-only characters")
def given_runner_ascii_only(ctx: QaContext) -> None:
    """Configure a QA runner with ASCII-only unsupported character check."""
    ctx.runner = DeterministicQaRunner()
    ctx.runner.configure_check(
        "unsupported_characters",
        QaSeverity.CRITICAL,
        {
            "allowed_ranges": ["U+0000-U+007F"],
            "allow_common_punctuation": True,
        },
    )


@when("I run QA checks")
def when_run_qa_checks(ctx: QaContext) -> None:
    """Execute the configured QA checks against the translated lines."""
    assert ctx.runner is not None
    assert ctx.lines is not None
    ctx.issues = ctx.runner.run_checks(ctx.lines)


@when("I build a runner from config and run checks")
def when_build_runner_from_config(ctx: QaContext) -> None:
    """Build a QA runner from config and execute checks against the lines."""
    assert ctx.config is not None
    assert ctx.lines is not None
    ctx.runner = DeterministicQaRunner()
    for check_config in ctx.config.checks:
        if check_config.enabled:
            ctx.runner.configure_check(
                check_config.check_name,
                check_config.severity,
                check_config.parameters,
            )
    ctx.issues = ctx.runner.run_checks(ctx.lines)


@then("issues are detected for problematic lines")
def then_issues_detected_for_problematic(ctx: QaContext) -> None:
    """Assert QA issues were detected for the expected problematic lines."""
    assert ctx.issues is not None
    line_ids_with_issues = {issue.line_id for issue in ctx.issues}
    assert "line_2" in line_ids_with_issues  # Too long
    assert "line_3" in line_ids_with_issues  # Unsupported chars


@then("clean lines have no issues")
def then_clean_lines_no_issues(ctx: QaContext) -> None:
    """Assert no QA issues were reported for clean lines."""
    assert ctx.issues is not None
    line_ids_with_issues = {issue.line_id for issue in ctx.issues}
    assert "line_1" not in line_ids_with_issues


@then("no issues are reported")
def then_no_issues(ctx: QaContext) -> None:
    """Assert no QA issues were reported at all."""
    assert ctx.issues is not None
    assert ctx.issues == []


@then("only the enabled check produces issues")
def then_only_enabled_check(ctx: QaContext) -> None:
    """Assert only the enabled check produced issues, not the disabled one."""
    assert ctx.issues is not None
    line_ids = {issue.line_id for issue in ctx.issues}
    assert "line_1" in line_ids  # Line length (enabled)
    assert "line_2" not in line_ids  # OK
    assert "line_3" not in line_ids  # Unsupported check disabled


@then("severities match the configuration")
def then_severities_match(ctx: QaContext) -> None:
    """Assert issue severities match what was configured in the check config."""
    assert ctx.issues is not None
    line_1_issue = next(i for i in ctx.issues if i.line_id == "line_1")
    assert line_1_issue.severity == QaSeverity.MAJOR


@then("non-ASCII lines are flagged")
def then_non_ascii_flagged(ctx: QaContext) -> None:
    """Assert lines with non-ASCII characters are flagged as issues."""
    assert ctx.issues is not None
    line_ids = {issue.line_id for issue in ctx.issues}
    assert "line_1" not in line_ids  # ASCII only
    assert "line_2" in line_ids  # Japanese
    assert "line_3" in line_ids  # Mixed


@then("issue metadata includes character details")
def then_metadata_includes_details(ctx: QaContext) -> None:
    """Assert issue metadata includes unsupported character count details."""
    assert ctx.issues is not None
    line_2_issue = next(i for i in ctx.issues if i.line_id == "line_2")
    assert line_2_issue.metadata is not None
    assert line_2_issue.metadata["unsupported_count"] == 5  # 5 Japanese chars


@then("all issues have FORMATTING category")
def then_all_formatting_category(ctx: QaContext) -> None:
    """Assert all reported issues have the FORMATTING category."""
    assert ctx.issues is not None
    for issue in ctx.issues:
        assert issue.category == QaCategory.FORMATTING


@then("all issues have valid structure")
def then_all_valid_structure(ctx: QaContext) -> None:
    """Assert all reported issues have required fields populated."""
    assert ctx.issues is not None
    for issue in ctx.issues:
        assert issue.issue_id is not None
        assert issue.line_id is not None
        assert issue.message is not None
        assert len(issue.message) > 0
