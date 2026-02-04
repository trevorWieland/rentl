"""Tests for untranslated line QA check."""

from __future__ import annotations

from rentl_core.qa.checks.untranslated_line import UntranslatedLineCheck
from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import QaSeverity


def test_untranslated_line_detected() -> None:
    """Detect when translated text matches source text."""
    check = UntranslatedLineCheck()
    line = TranslatedLine(line_id="line_001", text="Hello", source_text="Hello")

    results = check.check_line(line, QaSeverity.MINOR)

    assert len(results) == 1
    assert results[0].line_id == "line_001"


def test_untranslated_line_ignored_when_different() -> None:
    """Do not flag when translated text differs from source text."""
    check = UntranslatedLineCheck()
    line = TranslatedLine(line_id="line_001", text="Bonjour", source_text="Hello")

    results = check.check_line(line, QaSeverity.MINOR)

    assert results == []


def test_untranslated_line_ignored_without_source() -> None:
    """Do not flag when source_text is unavailable."""
    check = UntranslatedLineCheck()
    line = TranslatedLine(line_id="line_001", text="Hello", source_text=None)

    results = check.check_line(line, QaSeverity.MINOR)

    assert results == []
