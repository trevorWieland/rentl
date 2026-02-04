"""Unit tests for check registry."""

import pytest

from rentl_core.qa.checks.line_length import LineLengthCheck
from rentl_core.qa.registry import CheckRegistry, get_default_registry


class TestCheckRegistry:
    """Tests for CheckRegistry."""

    def test_register_and_create(self) -> None:
        """Register and create a check."""
        registry = CheckRegistry()
        registry.register("test_check", LineLengthCheck)

        check = registry.create("test_check")
        assert isinstance(check, LineLengthCheck)
        assert check.check_name == "line_length"

    def test_register_duplicate_raises(self) -> None:
        """Registering duplicate name raises."""
        registry = CheckRegistry()
        registry.register("test_check", LineLengthCheck)

        with pytest.raises(ValueError, match="already registered"):
            registry.register("test_check", LineLengthCheck)

    def test_create_unknown_raises(self) -> None:
        """Creating unknown check raises."""
        registry = CheckRegistry()

        with pytest.raises(ValueError, match="Unknown check"):
            registry.create("nonexistent")

    def test_list_checks_empty(self) -> None:
        """List checks returns empty list when none registered."""
        registry = CheckRegistry()
        assert registry.list_checks() == []

    def test_list_checks_sorted(self) -> None:
        """List checks returns sorted names."""
        registry = CheckRegistry()
        registry.register("zebra", LineLengthCheck)
        registry.register("alpha", LineLengthCheck)
        registry.register("middle", LineLengthCheck)

        assert registry.list_checks() == ["alpha", "middle", "zebra"]


class TestDefaultRegistry:
    """Tests for get_default_registry."""

    def test_default_registry_has_all_checks(self) -> None:
        """Default registry includes all built-in checks."""
        registry = get_default_registry()
        checks = registry.list_checks()

        assert "line_length" in checks
        assert "empty_translation" in checks
        assert "untranslated_line" in checks
        assert "whitespace" in checks
        assert "unsupported_characters" in checks

    def test_default_registry_creates_valid_checks(self) -> None:
        """Default registry creates working check instances."""
        registry = get_default_registry()

        for name in registry.list_checks():
            check = registry.create(name)
            assert check.check_name == name
