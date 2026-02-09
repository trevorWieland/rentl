"""Secret redaction for logs and artifacts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING

from pydantic import Field

from rentl_schemas.base import BaseSchema

if TYPE_CHECKING:
    # Recursive type for JSON-like data structures
    JsonValue = (
        str | int | float | bool | dict[str, "JsonValue"] | list["JsonValue"] | None
    )


class SecretPattern(BaseSchema):
    """Compiled regex pattern for detecting secrets."""

    pattern: str = Field(..., description="Regex pattern string")
    label: str = Field(..., description="Human-readable description")
    compiled: re.Pattern[str] | None = Field(
        default=None, description="Compiled regex (set during initialization)"
    )

    def model_post_init(self, __context: dict[str, str] | None) -> None:
        """Compile the pattern after initialization."""
        if self.compiled is None:
            self.compiled = re.compile(self.pattern)


class RedactionConfig(BaseSchema):
    """Configuration for secret redaction."""

    patterns: list[SecretPattern] = Field(
        default_factory=list, description="List of secret patterns to detect"
    )
    env_var_names: list[str] = Field(
        default_factory=list,
        description="Env var names whose values should be redacted",
    )


# Default patterns for common secret formats
DEFAULT_PATTERNS = [
    SecretPattern(
        pattern=r"sk-[a-zA-Z0-9]{20,}",
        label="OpenAI-style API key (sk-*)",
    ),
    SecretPattern(
        pattern=r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}",
        label="Bearer token",
    ),
    SecretPattern(
        pattern=r"(?:api[_-]?key|apikey|key)\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        label="API key assignment",
    ),
    SecretPattern(
        pattern=r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])",
        label="Base64 blob (40+ chars)",
    ),
]


class Redactor:
    """Redacts secrets from strings and dicts."""

    def __init__(
        self, patterns: list[SecretPattern], literal_values: list[str]
    ) -> None:
        """Initialize with patterns and literal secret values.

        Args:
            patterns: List of SecretPattern instances with compiled regexes
            literal_values: Exact string values to redact
                (e.g., resolved env var values)
        """
        self.patterns = patterns
        # Sort literal values by length (longest first) to avoid partial matches
        self.literal_values = sorted(literal_values, key=len, reverse=True)

    def redact(self, value: str) -> str:
        """Redact secrets from a string.

        Args:
            value: String that may contain secrets

        Returns:
            String with secrets replaced by [REDACTED]
        """
        result: str = value

        # First, redact literal env var values
        for literal in self.literal_values:
            if literal:  # Skip empty strings
                result = str(result).replace(str(literal), "[REDACTED]")

        # Then apply pattern-based redaction
        for pattern in self.patterns:
            if pattern.compiled is not None:
                result = pattern.compiled.sub("[REDACTED]", result)

        return result

    def redact_dict(self, data: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        """Deep-walk a dict and redact all string values.

        Args:
            data: Dictionary that may contain secrets

        Returns:
            New dictionary with secrets redacted
        """
        result: dict[str, JsonValue] = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact(value)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value)
            elif isinstance(value, list):
                result[key] = self._redact_list(value)
            else:
                result[key] = value
        return result

    def _redact_list(self, items: list[JsonValue]) -> list[JsonValue]:
        """Recursively redact all string values in a list.

        Args:
            items: List that may contain secrets in strings or nested structures

        Returns:
            New list with secrets redacted
        """
        result: list[JsonValue] = []
        for item in items:
            if isinstance(item, str):
                result.append(self.redact(item))
            elif isinstance(item, dict):
                result.append(self.redact_dict(item))
            elif isinstance(item, list):
                result.append(self._redact_list(item))
            else:
                result.append(item)
        return result


def build_redactor(config: RedactionConfig, env_values: dict[str, str]) -> Redactor:
    """Build a Redactor from config and resolved env var values.

    Args:
        config: RedactionConfig with patterns and env var names
        env_values: Dictionary of environment variable values (key=name, value=secret)

    Returns:
        Redactor instance ready to use
    """
    # Use default patterns if none provided
    patterns = config.patterns or DEFAULT_PATTERNS

    # Collect literal values from env vars
    literal_values = [
        env_values[name] for name in config.env_var_names if name in env_values
    ]

    return Redactor(patterns=patterns, literal_values=literal_values)


def redact_secrets(value: str, config: RedactionConfig | None = None) -> str:
    """Convenience function to redact secrets from a string.

    Args:
        value: String that may contain secrets
        config: Optional RedactionConfig (uses defaults if not provided)

    Returns:
        String with secrets replaced by [REDACTED]
    """
    if config is None:
        config = RedactionConfig()
    redactor = build_redactor(config, {})
    return redactor.redact(value)
