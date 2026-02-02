"""Unit tests for line length check."""

import pytest

from rentl_core.qa.checks.line_length import LineLengthCheck
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import QaCategory, QaSeverity


def _make_line(text: str, line_id: str = "line_1") -> TranslatedLine:
    return TranslatedLine(line_id=line_id, text=text)


class TestLineLengthCheck:
    """Tests for LineLengthCheck."""

    def test_check_name(self) -> None:
        """Check has correct name."""
        check = LineLengthCheck()
        assert check.check_name == "line_length"

    def test_category(self) -> None:
        """Check uses FORMATTING category."""
        check = LineLengthCheck()
        assert check.category == QaCategory.FORMATTING

    def test_configure_requires_max_length(self) -> None:
        """Configure raises without max_length."""
        check = LineLengthCheck()
        with pytest.raises(ValueError, match="requires max_length"):
            check.configure(None)
        with pytest.raises(ValueError, match="requires max_length"):
            check.configure({})

    def test_configure_max_length_must_be_positive(self) -> None:
        """Configure validates max_length is positive."""
        check = LineLengthCheck()
        with pytest.raises(ValueError, match="positive integer"):
            check.configure({"max_length": 0})
        with pytest.raises(ValueError, match="positive integer"):
            check.configure({"max_length": -1})
        with pytest.raises(ValueError, match="positive integer"):
            check.configure({"max_length": "10"})

    def test_configure_valid_parameters(self) -> None:
        """Configure accepts valid parameters."""
        check = LineLengthCheck()
        check.configure({"max_length": 10})
        # Should not raise

    def test_configure_count_mode_validation(self) -> None:
        """Configure validates count_mode."""
        check = LineLengthCheck()
        with pytest.raises(ValueError, match="count_mode"):
            check.configure({"max_length": 10, "count_mode": "words"})

    def test_check_line_not_configured(self) -> None:
        """Check raises if not configured."""
        check = LineLengthCheck()
        line = _make_line("Hello")
        with pytest.raises(ValueError, match="not configured"):
            check.check_line(line, QaSeverity.MAJOR)

    def test_line_within_limit_passes(self) -> None:
        """Line within limit produces no issues."""
        check = LineLengthCheck()
        check.configure({"max_length": 10})
        line = _make_line("Hello")
        results = check.check_line(line, QaSeverity.MAJOR)
        assert results == []

    def test_line_at_limit_passes(self) -> None:
        """Line exactly at limit produces no issues."""
        check = LineLengthCheck()
        check.configure({"max_length": 5})
        line = _make_line("Hello")
        results = check.check_line(line, QaSeverity.MAJOR)
        assert results == []

    def test_line_exceeds_limit(self) -> None:
        """Line exceeding limit produces issue."""
        check = LineLengthCheck()
        check.configure({"max_length": 5})
        line = _make_line("Hello World", line_id="line_1")
        results = check.check_line(line, QaSeverity.MAJOR)

        assert len(results) == 1
        result = results[0]
        assert result.line_id == "line_1"
        assert result.category == QaCategory.FORMATTING
        assert result.severity == QaSeverity.MAJOR
        assert "11" in result.message  # actual length
        assert "5" in result.message  # max length
        assert result.metadata is not None
        assert result.metadata["actual_length"] == 11
        assert result.metadata["max_length"] == 5

    def test_count_mode_characters(self) -> None:
        """Characters mode counts unicode characters."""
        check = LineLengthCheck()
        check.configure({"max_length": 5, "count_mode": "characters"})
        # "こんにちは" is 5 characters
        line = _make_line("こんにちは")
        results = check.check_line(line, QaSeverity.MAJOR)
        assert results == []

    def test_count_mode_bytes(self) -> None:
        """Bytes mode counts UTF-8 bytes."""
        check = LineLengthCheck()
        check.configure({"max_length": 10, "count_mode": "bytes"})
        # "こんにちは" is 15 bytes in UTF-8 (3 bytes per character)
        line = _make_line("こんにちは")
        results = check.check_line(line, QaSeverity.MAJOR)

        assert len(results) == 1
        result = results[0]
        assert result.metadata is not None
        assert result.metadata["actual_length"] == 15
        assert result.metadata["count_mode"] == "bytes"

    def test_severity_passed_through(self) -> None:
        """Configured severity is used in results."""
        check = LineLengthCheck()
        check.configure({"max_length": 5})
        line = _make_line("Hello World")

        for severity in [QaSeverity.INFO, QaSeverity.MINOR, QaSeverity.CRITICAL]:
            results = check.check_line(line, severity)
            assert results[0].severity == severity
