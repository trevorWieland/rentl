"""Unit tests for empty translation check.

Note: TranslatedLine schema has min_length=1 for text field, so empty
strings cannot be created. These tests verify the check behavior with
valid lines (happy path only - the schema prevents empty lines).
"""

from rentl_core.qa.checks.empty_translation import EmptyTranslationCheck
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import QaCategory, QaSeverity


def _make_line(text: str, line_id: str = "line_1") -> TranslatedLine:
    return TranslatedLine(line_id=line_id, text=text)


class TestEmptyTranslationCheck:
    """Tests for EmptyTranslationCheck."""

    def test_check_name(self) -> None:
        """Check has correct name."""
        check = EmptyTranslationCheck()
        assert check.check_name == "empty_translation"

    def test_category(self) -> None:
        """Check uses FORMATTING category."""
        check = EmptyTranslationCheck()
        assert check.category == QaCategory.FORMATTING

    def test_configure_accepts_none(self) -> None:
        """Configure accepts None parameters."""
        check = EmptyTranslationCheck()
        check.configure(None)
        # Should not raise

    def test_configure_accepts_empty(self) -> None:
        """Configure accepts empty parameters."""
        check = EmptyTranslationCheck()
        check.configure({})
        # Should not raise

    def test_non_empty_line_passes(self) -> None:
        """Non-empty line produces no issues."""
        check = EmptyTranslationCheck()
        check.configure(None)
        line = _make_line("Hello World")
        results = check.check_line(line, QaSeverity.CRITICAL)
        assert results == []

    def test_single_character_passes(self) -> None:
        """Single character line produces no issues."""
        check = EmptyTranslationCheck()
        check.configure(None)
        line = _make_line("X")
        results = check.check_line(line, QaSeverity.CRITICAL)
        assert results == []

    def test_line_with_content_passes(self) -> None:
        """Line with actual content passes."""
        check = EmptyTranslationCheck()
        check.configure(None)
        line = _make_line("This is a valid translation")
        results = check.check_line(line, QaSeverity.CRITICAL)
        assert results == []

    def test_unicode_content_passes(self) -> None:
        """Unicode content passes."""
        check = EmptyTranslationCheck()
        check.configure(None)
        line = _make_line("こんにちは")
        results = check.check_line(line, QaSeverity.CRITICAL)
        assert results == []
