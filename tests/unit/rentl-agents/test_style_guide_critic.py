"""Unit tests for StyleGuideViolation schema and agent behavior."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rentl_schemas.phases import StyleGuideViolation, StyleGuideViolationList


class TestStyleGuideViolationSchema:
    """Test cases for StyleGuideViolation Pydantic schema."""

    def test_valid_violation(self) -> None:
        """Test creating a valid style guide violation."""
        violation = StyleGuideViolation(
            line_id="line_001",
            violation_type="honorific",
            rule_violated="Preserve Japanese honorifics",
            source_text="田中さん",
            translation_text="Mr. Tanaka",
            explanation="Honorific -san was anglicized to Mr.",
            suggestion="Use 'Tanaka-san' instead",
        )

        assert violation.line_id == "line_001"
        assert violation.violation_type == "honorific"
        assert violation.rule_violated == "Preserve Japanese honorifics"
        assert violation.source_text == "田中さん"
        assert violation.translation_text == "Mr. Tanaka"
        assert violation.explanation == "Honorific -san was anglicized to Mr."
        assert violation.suggestion == "Use 'Tanaka-san' instead"

    def test_valid_violation_types(self) -> None:
        """Test all valid violation types."""
        valid_types = [
            "honorific",
            "formality",
            "terminology",
            "cultural",
            "consistency",
            "other",
        ]

        for violation_type in valid_types:
            violation = StyleGuideViolation(
                line_id="line_001",
                violation_type=violation_type,
                rule_violated="Test rule",
                source_text="Source",
                translation_text="Translation",
                explanation="Test explanation",
            )
            assert violation.violation_type == violation_type

    def test_invalid_violation_type_raises(self) -> None:
        """Test that invalid violation type raises error."""
        with pytest.raises(ValidationError, match="violation_type"):
            StyleGuideViolation(
                line_id="line_001",
                violation_type="invalid_type",  # Not in allowed list
                rule_violated="Test rule",
                source_text="Source",
                translation_text="Translation",
                explanation="Test explanation",
            )

    def test_optional_suggestion(self) -> None:
        """Test that suggestion is optional."""
        violation = StyleGuideViolation(
            line_id="line_001",
            violation_type="other",
            rule_violated="Test rule",
            source_text="Source",
            translation_text="Translation",
            explanation="Test explanation",
            # No suggestion provided
        )

        assert violation.suggestion is None

    def test_empty_rule_violated_raises(self) -> None:
        """Test that empty rule_violated raises error."""
        with pytest.raises(ValidationError, match="rule_violated"):
            StyleGuideViolation(
                line_id="line_001",
                violation_type="other",
                rule_violated="",  # Empty string
                source_text="Source",
                translation_text="Translation",
                explanation="Test explanation",
            )

    def test_empty_source_text_raises(self) -> None:
        """Test that empty source_text raises error."""
        with pytest.raises(ValidationError, match="source_text"):
            StyleGuideViolation(
                line_id="line_001",
                violation_type="other",
                rule_violated="Test rule",
                source_text="",  # Empty string
                translation_text="Translation",
                explanation="Test explanation",
            )

    def test_empty_translation_text_raises(self) -> None:
        """Test that empty translation_text raises error."""
        with pytest.raises(ValidationError, match="translation_text"):
            StyleGuideViolation(
                line_id="line_001",
                violation_type="other",
                rule_violated="Test rule",
                source_text="Source",
                translation_text="",  # Empty string
                explanation="Test explanation",
            )

    def test_empty_explanation_raises(self) -> None:
        """Test that empty explanation raises error."""
        with pytest.raises(ValidationError, match="explanation"):
            StyleGuideViolation(
                line_id="line_001",
                violation_type="other",
                rule_violated="Test rule",
                source_text="Source",
                translation_text="Translation",
                explanation="",  # Empty string
            )


class TestStyleGuideViolationListSchema:
    """Test cases for StyleGuideViolationList Pydantic schema."""

    def test_empty_violations_list(self) -> None:
        """Test creating an empty violations list."""
        violation_list = StyleGuideViolationList(violations=[])

        assert violation_list.violations == []

    def test_default_factory_empty(self) -> None:
        """Test that default factory creates empty list."""
        violation_list = StyleGuideViolationList()

        assert violation_list.violations == []

    def test_multiple_violations(self) -> None:
        """Test list with multiple violations."""
        violations = [
            StyleGuideViolation(
                line_id="line_001",
                violation_type="honorific",
                rule_violated="Rule 1",
                source_text="Source 1",
                translation_text="Translation 1",
                explanation="Explanation 1",
            ),
            StyleGuideViolation(
                line_id="line_002",
                violation_type="formality",
                rule_violated="Rule 2",
                source_text="Source 2",
                translation_text="Translation 2",
                explanation="Explanation 2",
            ),
        ]

        violation_list = StyleGuideViolationList(violations=violations)

        assert len(violation_list.violations) == 2
        assert violation_list.violations[0].line_id == "line_001"
        assert violation_list.violations[1].line_id == "line_002"


class TestEmptyStyleGuideHandling:
    """Test cases for agent behavior with empty style guide."""

    def test_empty_violations_is_valid_response(self) -> None:
        """Test that empty violations list is a valid agent response.

        When no style guide is provided, the agent should return an empty
        violations list rather than an error.
        """
        # This represents what the agent should return when:
        # 1. No style guide is provided
        # 2. The style guide is empty
        # 3. No violations are found

        result = StyleGuideViolationList(violations=[])

        assert result.violations == []
        assert len(result.violations) == 0
