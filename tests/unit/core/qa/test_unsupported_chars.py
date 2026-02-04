"""Unit tests for unsupported character check."""

import pytest

from rentl_core.qa.checks.unsupported_chars import UnsupportedCharacterCheck
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import QaCategory, QaSeverity


def _make_line(text: str, line_id: str = "line_1") -> TranslatedLine:
    return TranslatedLine(line_id=line_id, text=text)


class TestUnsupportedCharacterCheck:
    """Tests for UnsupportedCharacterCheck."""

    def test_check_name(self) -> None:
        """Check has correct name."""
        check = UnsupportedCharacterCheck()
        assert check.check_name == "unsupported_characters"

    def test_category(self) -> None:
        """Check uses FORMATTING category."""
        check = UnsupportedCharacterCheck()
        assert check.category == QaCategory.FORMATTING

    def test_configure_requires_allowed_ranges(self) -> None:
        """Configure raises without allowed_ranges."""
        check = UnsupportedCharacterCheck()
        with pytest.raises(ValueError, match="requires allowed_ranges"):
            check.configure(None)
        with pytest.raises(ValueError, match="non-empty list"):
            check.configure({"allowed_ranges": []})
        with pytest.raises(ValueError, match="non-empty list"):
            check.configure({"allowed_ranges": "not a list"})

    def test_check_line_not_configured(self) -> None:
        """Check raises if not configured."""
        check = UnsupportedCharacterCheck()
        line = _make_line("Hello")
        with pytest.raises(ValueError, match="not configured"):
            check.check_line(line, QaSeverity.MAJOR)

    def test_range_format_parsing(self) -> None:
        """Parse U+XXXX-U+XXXX range format."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": ["U+0041-U+005A"],  # A-Z
            "allow_common_punctuation": False,
        })
        # A, Z should pass
        assert check.check_line(_make_line("A"), QaSeverity.MAJOR) == []
        assert check.check_line(_make_line("Z"), QaSeverity.MAJOR) == []
        # a (lowercase) should fail
        results = check.check_line(_make_line("a"), QaSeverity.MAJOR)
        assert len(results) == 1

    def test_single_codepoint_format(self) -> None:
        """Parse U+XXXX single codepoint format."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": ["U+0041"],  # Just 'A'
            "allow_common_punctuation": False,
        })
        assert check.check_line(_make_line("A"), QaSeverity.MAJOR) == []
        assert len(check.check_line(_make_line("B"), QaSeverity.MAJOR)) == 1

    def test_literal_characters(self) -> None:
        """Parse literal characters."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": ["ABC"],  # Literal A, B, C
            "allow_common_punctuation": False,
        })
        assert check.check_line(_make_line("ABC"), QaSeverity.MAJOR) == []
        assert len(check.check_line(_make_line("D"), QaSeverity.MAJOR)) == 1

    def test_invalid_range_format(self) -> None:
        """Invalid range specification raises error."""
        check = UnsupportedCharacterCheck()
        with pytest.raises(ValueError, match="start > end"):
            check.configure({
                "allowed_ranges": ["U+005A-U+0041"],  # Z-A (invalid)
                "allow_common_punctuation": False,
            })

    def test_common_punctuation_included_by_default(self) -> None:
        """Common punctuation allowed by default."""
        check = UnsupportedCharacterCheck()
        check.configure({"allowed_ranges": ["U+0041-U+005A"]})  # A-Z only

        # Space, period, comma should pass with default punctuation
        assert check.check_line(_make_line("A B"), QaSeverity.MAJOR) == []
        assert check.check_line(_make_line("A.B"), QaSeverity.MAJOR) == []
        assert check.check_line(_make_line("A,B"), QaSeverity.MAJOR) == []

    def test_common_punctuation_disabled(self) -> None:
        """Common punctuation can be disabled."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": ["U+0041-U+005A"],
            "allow_common_punctuation": False,
        })

        # Space should fail without common punctuation
        results = check.check_line(_make_line("A B"), QaSeverity.MAJOR)
        assert len(results) == 1
        assert " " in results[0].message

    def test_all_supported_passes(self) -> None:
        """Line with all supported characters passes."""
        check = UnsupportedCharacterCheck()
        check.configure({"allowed_ranges": ["U+0000-U+007F"]})  # ASCII
        line = _make_line("Hello, World!")
        results = check.check_line(line, QaSeverity.MAJOR)
        assert results == []

    def test_unsupported_character_detected(self) -> None:
        """Unsupported character produces issue."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": ["U+0000-U+007F"],  # ASCII only
            "allow_common_punctuation": False,
        })
        line = _make_line("Hello日本", line_id="line_1")  # Japanese characters
        results = check.check_line(line, QaSeverity.MAJOR)

        assert len(results) == 1
        result = results[0]
        assert result.line_id == "line_1"
        assert result.category == QaCategory.FORMATTING
        assert result.severity == QaSeverity.MAJOR
        assert "unsupported" in result.message.lower()
        assert result.metadata is not None
        assert result.metadata["unsupported_count"] == 2

    def test_multiple_ranges(self) -> None:
        """Multiple ranges can be combined."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": [
                "U+0041-U+005A",  # A-Z
                "U+0061-U+007A",  # a-z
            ],
            "allow_common_punctuation": False,
        })
        assert check.check_line(_make_line("AaBbZz"), QaSeverity.MAJOR) == []
        # Number should fail
        results = check.check_line(_make_line("A1"), QaSeverity.MAJOR)
        assert len(results) == 1

    def test_cjk_range(self) -> None:
        """CJK ranges work correctly."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": [
                "U+3040-U+309F",  # Hiragana
                "U+30A0-U+30FF",  # Katakana
            ],
            "allow_common_punctuation": False,
        })
        assert check.check_line(_make_line("こんにちは"), QaSeverity.MAJOR) == []
        assert check.check_line(_make_line("カタカナ"), QaSeverity.MAJOR) == []
        # Kanji should fail
        results = check.check_line(_make_line("漢字"), QaSeverity.MAJOR)
        assert len(results) == 1

    def test_metadata_includes_character_details(self) -> None:
        """Metadata includes details about unsupported characters."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": ["U+0041-U+005A"],  # A-Z only
            "allow_common_punctuation": False,
        })
        line = _make_line("ABCabc")  # a, b, c are unsupported
        results = check.check_line(line, QaSeverity.MAJOR)

        assert len(results) == 1
        metadata = results[0].metadata
        assert metadata is not None
        assert metadata["unsupported_count"] == 3
        unsupported_chars = metadata["unsupported_chars"]
        assert isinstance(unsupported_chars, list)
        assert len(unsupported_chars) == 3
        # Check first unsupported char
        first = unsupported_chars[0]
        assert isinstance(first, dict)
        assert first["position"] == 3
        assert first["char"] == "a"
        assert first["codepoint"] == "U+0061"

    def test_severity_passed_through(self) -> None:
        """Configured severity is used in results."""
        check = UnsupportedCharacterCheck()
        check.configure({
            "allowed_ranges": ["U+0041-U+005A"],
            "allow_common_punctuation": False,
        })
        line = _make_line("a")

        for severity in [QaSeverity.INFO, QaSeverity.MINOR, QaSeverity.CRITICAL]:
            results = check.check_line(line, severity)
            assert results[0].severity == severity
