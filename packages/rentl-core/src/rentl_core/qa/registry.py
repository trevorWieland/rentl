"""Registry for deterministic QA checks."""

from __future__ import annotations

from collections.abc import Callable

from rentl_core.qa.checks.empty_translation import EmptyTranslationCheck
from rentl_core.qa.checks.line_length import LineLengthCheck
from rentl_core.qa.checks.unsupported_chars import UnsupportedCharacterCheck
from rentl_core.qa.checks.whitespace import WhitespaceCheck
from rentl_core.qa.protocol import DeterministicCheck

type CheckFactory = Callable[[], DeterministicCheck]


class CheckRegistry:
    """Registry for deterministic QA check factories.

    The registry maintains a mapping of check names to factory functions
    that create check instances. This allows checks to be configured and
    instantiated by name from configuration.
    """

    def __init__(self) -> None:
        """Initialize an empty check registry."""
        self._factories: dict[str, CheckFactory] = {}

    def register(self, name: str, factory: CheckFactory) -> None:
        """Register a check factory.

        Args:
            name: Unique check name.
            factory: Callable that creates a check instance.

        Raises:
            ValueError: If a check with this name is already registered.
        """
        if name in self._factories:
            raise ValueError(f"Check already registered: {name}")
        self._factories[name] = factory

    def create(self, name: str) -> DeterministicCheck:
        """Create a check instance by name.

        Args:
            name: Name of the check to create.

        Returns:
            New check instance.

        Raises:
            ValueError: If the check name is not registered.
        """
        factory = self._factories.get(name)
        if factory is None:
            raise ValueError(f"Unknown check: {name}")
        return factory()

    def list_checks(self) -> list[str]:
        """List all registered check names.

        Returns:
            Sorted list of registered check names.
        """
        return sorted(self._factories.keys())


def get_default_registry() -> CheckRegistry:
    """Get the default check registry with all built-in checks.

    Returns:
        CheckRegistry with all standard checks registered.
    """
    registry = CheckRegistry()
    registry.register("line_length", LineLengthCheck)
    registry.register("empty_translation", EmptyTranslationCheck)
    registry.register("whitespace", WhitespaceCheck)
    registry.register("unsupported_characters", UnsupportedCharacterCheck)
    return registry
