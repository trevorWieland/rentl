"""Tests for style guide critic agent and schema."""

import pytest
from pydantic import ValidationError

from rentl_schemas.phases import (
    StyleGuideReviewLine,
    StyleGuideReviewList,
    StyleGuideRuleViolation,
    StyleGuideViolation,
    StyleGuideViolationList,
)


class TestStyleGuideViolationSchema:
    """Test cases for StyleGuideViolation Pydantic schema."""

    def test_basic_violation(self) -> None:
        """Test creating a basic violation with all required fields."""
        violation = StyleGuideViolation(
            line_id="line_001",
            rule_violated="Test rule",
            explanation="Test explanation",
        )

        assert violation.line_id == "line_001"
        assert violation.rule_violated == "Test rule"
        assert violation.explanation == "Test explanation"

    def test_empty_rule_violated_raises(self) -> None:
        """Test that empty rule_violated raises error."""
        with pytest.raises(ValidationError, match="rule_violated"):
            StyleGuideViolation(
                line_id="line_001",
                rule_violated="",
                explanation="Test explanation",
            )

    def test_empty_explanation_raises(self) -> None:
        """Test that empty explanation raises error."""
        with pytest.raises(ValidationError, match="explanation"):
            StyleGuideViolation(
                line_id="line_001",
                rule_violated="Test rule",
                explanation="",
            )


class TestStyleGuideViolationListSchema:
    """Test cases for StyleGuideViolationList Pydantic schema."""

    def test_empty_violations_list(self) -> None:
        """Test creating an empty violations list."""
        violation_list = StyleGuideViolationList(violations=[])
        assert len(violation_list.violations) == 0

    def test_single_violation(self) -> None:
        """Test list with single violation."""
        violation = StyleGuideViolation(
            line_id="line_001",
            rule_violated="Rule 1",
            explanation="Explanation 1",
        )

        violation_list = StyleGuideViolationList(violations=[violation])

        assert len(violation_list.violations) == 1
        assert violation_list.violations[0].line_id == "line_001"

    def test_multiple_violations(self) -> None:
        """Test list with multiple violations."""
        violations = [
            StyleGuideViolation(
                line_id="line_001",
                rule_violated="Rule 1",
                explanation="Explanation 1",
            ),
            StyleGuideViolation(
                line_id="line_002",
                rule_violated="Rule 2",
                explanation="Explanation 2",
            ),
        ]

        violation_list = StyleGuideViolationList(violations=violations)

        assert len(violation_list.violations) == 2
        assert violation_list.violations[0].line_id == "line_001"
        assert violation_list.violations[1].line_id == "line_002"

    def test_violations_default_to_empty(self) -> None:
        """Test that violations default to empty list."""
        violation_list = StyleGuideViolationList()
        assert violation_list.violations == []


class TestStyleGuideReviewListSchema:
    """Test cases for StyleGuideReviewList Pydantic schema."""

    def test_review_line_with_empty_violations(self) -> None:
        """Test review line accepts empty violations list."""
        review_line = StyleGuideReviewLine(line_id="line_001", violations=[])
        review_list = StyleGuideReviewList(reviews=[review_line])

        assert len(review_list.reviews) == 1
        assert review_list.reviews[0].line_id == "line_001"
        assert review_list.reviews[0].violations == []

    def test_review_line_with_violation(self) -> None:
        """Test review line accepts rule violations."""
        violation = StyleGuideRuleViolation(
            rule_violated="Preserve honorifics",
            explanation="-san was removed",
        )
        review_line = StyleGuideReviewLine(
            line_id="line_002",
            violations=[violation],
        )
        review_list = StyleGuideReviewList(reviews=[review_line])

        assert review_list.reviews[0].line_id == "line_002"
        assert (
            review_list.reviews[0].violations[0].rule_violated == "Preserve honorifics"
        )
