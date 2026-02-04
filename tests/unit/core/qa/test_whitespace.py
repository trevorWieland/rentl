"""Unit tests for whitespace check.

Note: TranslatedLine schema has str_strip_whitespace=True in BaseSchema,
so leading/trailing whitespace is stripped during validation. These tests
verify the check behavior with valid lines (happy path only - the schema
prevents whitespace issues).
"""

from rentl_core.qa.checks.whitespace import WhitespaceCheck
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import QaCategory, QaSeverity


def _make_line(text: str, line_id: str = "line_1") -> TranslatedLine:
    return TranslatedLine(line_id=line_id, text=text)


class TestWhitespaceCheck:
    """Tests for WhitespaceCheck."""

    def test_check_name(self) -> None:
        """Check has correct name."""
        check = WhitespaceCheck()
        assert check.check_name == "whitespace"

    def test_category(self) -> None:
        """Check uses FORMATTING category."""
        check = WhitespaceCheck()
        assert check.category == QaCategory.FORMATTING

    def test_configure_accepts_none(self) -> None:
        """Configure accepts None parameters."""
        check = WhitespaceCheck()
        check.configure(None)
        # Should not raise

    def test_clean_line_passes(self) -> None:
        """Line without extra whitespace passes."""
        check = WhitespaceCheck()
        check.configure(None)
        line = _make_line("Hello World")
        results = check.check_line(line, QaSeverity.MINOR)
        assert results == []

    def test_internal_whitespace_ignored(self) -> None:
        """Internal whitespace (between words) not flagged."""
        check = WhitespaceCheck()
        check.configure(None)
        line = _make_line("Hello   World")  # Multiple internal spaces
        results = check.check_line(line, QaSeverity.MINOR)
        assert results == []

    def test_unicode_content_passes(self) -> None:
        """Unicode content without whitespace issues passes."""
        check = WhitespaceCheck()
        check.configure(None)
        line = _make_line("こんにちは 世界")
        results = check.check_line(line, QaSeverity.MINOR)
        assert results == []

    def test_multiple_spaces_between_words(self) -> None:
        """Multiple spaces between words is not flagged."""
        check = WhitespaceCheck()
        check.configure(None)
        line = _make_line("Hello    World    Test")
        results = check.check_line(line, QaSeverity.MINOR)
        assert results == []
