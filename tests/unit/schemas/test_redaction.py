"""Unit tests for secret redaction."""

import math
from typing import cast

from rentl_schemas.redaction import (
    DEFAULT_PATTERNS,
    RedactionConfig,
    Redactor,
    SecretPattern,
    build_redactor,
    redact_secrets,
)


def test_secret_pattern_compilation() -> None:
    """Ensure SecretPattern compiles regex on initialization."""
    pattern = SecretPattern(pattern=r"sk-[a-z]+", label="test pattern")
    assert pattern.compiled is not None
    assert pattern.compiled.pattern == r"sk-[a-z]+"


def test_redactor_literal_values() -> None:
    """Ensure Redactor redacts exact literal values."""
    redactor = Redactor(patterns=[], literal_values=["secret123", "token456"])

    result = redactor.redact("The secret is secret123 and token456")
    assert result == "The secret is [REDACTED] and [REDACTED]"


def test_redactor_literal_values_longest_first() -> None:
    """Ensure longer literals are matched first to avoid partial matches."""
    redactor = Redactor(
        patterns=[],
        literal_values=["secret", "secret123"],  # Order should not matter
    )

    # "secret123" should be matched as a whole, not as "secret" + "123"
    result = redactor.redact("Value: secret123")
    assert result == "Value: [REDACTED]"


def test_redactor_pattern_openai_key() -> None:
    """Ensure OpenAI-style keys (sk-*) are redacted."""
    pattern = SecretPattern(pattern=r"sk-[a-zA-Z0-9]{20,}", label="OpenAI key")
    redactor = Redactor(patterns=[pattern], literal_values=[])

    result = redactor.redact("API key: sk-abcdefghij1234567890")
    assert result == "API key: [REDACTED]"

    # Short sk- strings should not be redacted
    result = redactor.redact("sk-short")
    assert result == "sk-short"


def test_redactor_pattern_bearer_token() -> None:
    """Ensure Bearer tokens are redacted."""
    pattern = SecretPattern(
        pattern=r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", label="Bearer token"
    )
    redactor = Redactor(patterns=[pattern], literal_values=[])

    result = redactor.redact("Authorization: Bearer abc123def456ghi789jkl")
    assert result == "Authorization: [REDACTED]"


def test_redactor_pattern_api_key_assignment() -> None:
    """Ensure API key assignments are redacted."""
    pattern = SecretPattern(
        pattern=r"(?:api[_-]?key|apikey|key)\s*[=:]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        label="API key assignment",
    )
    redactor = Redactor(patterns=[pattern], literal_values=[])

    result = redactor.redact("api_key=abcdefghij1234567890")
    assert "[REDACTED]" in result

    result = redactor.redact('apikey: "abcdefghij1234567890xyz"')
    assert "[REDACTED]" in result


def test_redactor_pattern_base64_blob() -> None:
    """Ensure base64-encoded blobs (40+ chars) are redacted."""
    pattern = SecretPattern(
        pattern=r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])",
        label="Base64 blob",
    )
    redactor = Redactor(patterns=[pattern], literal_values=[])

    # 40+ character base64 string
    long_base64 = "dGhpcyBpcyBhIHZlcnkgbG9uZyBiYXNlNjQgZW5jb2RlZCBzdHJpbmcK"
    result = redactor.redact(f"Token: {long_base64}")
    assert result == "Token: [REDACTED]"

    # Short base64 should not be redacted
    short_base64 = "dGVzdA=="
    result = redactor.redact(f"Short: {short_base64}")
    assert result == f"Short: {short_base64}"


def test_redactor_default_patterns() -> None:
    """Ensure DEFAULT_PATTERNS covers common secret formats."""
    assert len(DEFAULT_PATTERNS) >= 4
    labels = [p.label for p in DEFAULT_PATTERNS]
    assert any("OpenAI" in label or "sk-" in label for label in labels)
    assert any("Bearer" in label for label in labels)
    assert any("API key" in label for label in labels)
    assert any("Base64" in label or "base64" in label for label in labels)


def test_redactor_dict_shallow() -> None:
    """Ensure redact_dict redacts string values in a shallow dict."""
    redactor = Redactor(patterns=[], literal_values=["secret123"])

    data = {"key1": "normal value", "key2": "secret123", "key3": 42}
    result = redactor.redact_dict(data)

    assert result["key1"] == "normal value"
    assert result["key2"] == "[REDACTED]"
    assert result["key3"] == 42


def test_redactor_dict_nested() -> None:
    """Ensure redact_dict recursively redacts nested dicts."""
    redactor = Redactor(patterns=[], literal_values=["secret123"])

    data = {
        "outer": {
            "inner": {"secret": "secret123", "safe": "ok"},
            "also_safe": "ok",
        }
    }
    result = redactor.redact_dict(data)

    outer = cast(dict[str, str | dict], result["outer"])
    inner = cast(dict[str, str], outer["inner"])
    assert inner["secret"] == "[REDACTED]"
    assert inner["safe"] == "ok"
    assert outer["also_safe"] == "ok"


def test_redactor_dict_with_list() -> None:
    """Ensure redact_dict redacts strings inside lists."""
    redactor = Redactor(patterns=[], literal_values=["secret123"])

    data = {
        "items": ["normal", "secret123", "also normal"],
        "count": 3,
    }
    result = redactor.redact_dict(data)

    assert result["items"] == ["normal", "[REDACTED]", "also normal"]
    assert result["count"] == 3


def test_redactor_dict_mixed_types() -> None:
    """Ensure redact_dict handles mixed types gracefully."""
    redactor = Redactor(patterns=[], literal_values=["secret123"])

    data = {
        "string": "secret123",
        "int": 42,
        "float": math.pi,
        "bool": True,
        "none": None,
        "list": [1, "secret123", None],
        "dict": {"nested": "secret123"},
    }
    result = redactor.redact_dict(data)

    assert result["string"] == "[REDACTED]"
    assert result["int"] == 42
    assert result["float"] == math.pi
    assert result["bool"] is True
    assert result["none"] is None
    assert result["list"] == [1, "[REDACTED]", None]
    nested_dict = cast(dict[str, str], result["dict"])
    assert nested_dict["nested"] == "[REDACTED]"


def test_env_var_names_not_redacted() -> None:
    """Ensure env var names (e.g., RENTL_OPENROUTER_API_KEY) are not redacted."""
    redactor = Redactor(
        patterns=DEFAULT_PATTERNS,
        literal_values=["actual-secret-value"],
    )

    # Env var name should NOT be redacted
    result = redactor.redact("Using env var: RENTL_OPENROUTER_API_KEY")
    assert "RENTL_OPENROUTER_API_KEY" in result

    # But the actual value should be redacted
    result = redactor.redact("Value: actual-secret-value")
    assert result == "Value: [REDACTED]"


def test_build_redactor_with_env_values() -> None:
    """Ensure build_redactor collects env var values for redaction."""
    config = RedactionConfig(
        patterns=[],
        env_var_names=["API_KEY", "TOKEN"],
    )
    env_values = {
        "API_KEY": "secret123",
        "TOKEN": "token456",
        "OTHER": "ignored",
    }

    redactor = build_redactor(config, env_values)
    result = redactor.redact("Keys: secret123 and token456")
    assert result == "Keys: [REDACTED] and [REDACTED]"


def test_build_redactor_uses_default_patterns() -> None:
    """Ensure build_redactor uses DEFAULT_PATTERNS if none provided."""
    config = RedactionConfig()
    redactor = build_redactor(config, {})

    # Should redact OpenAI-style keys
    result = redactor.redact("sk-abcdefghij1234567890")
    assert result == "[REDACTED]"


def test_build_redactor_with_custom_patterns() -> None:
    """Ensure build_redactor respects custom patterns when provided."""
    config = RedactionConfig(
        patterns=[
            SecretPattern(pattern=r"custom-[0-9]+", label="custom pattern"),
        ]
    )
    redactor = build_redactor(config, {})

    result = redactor.redact("Value: custom-12345")
    assert result == "Value: [REDACTED]"


def test_redact_secrets_convenience_function() -> None:
    """Ensure redact_secrets provides a simple API for basic use."""
    result = redact_secrets("API key: sk-abcdefghij1234567890")
    assert result == "API key: [REDACTED]"


def test_redact_secrets_with_config() -> None:
    """Ensure redact_secrets accepts custom config."""
    config = RedactionConfig(
        patterns=[
            SecretPattern(pattern=r"test-[0-9]+", label="test pattern"),
        ]
    )
    result = redact_secrets("Value: test-999", config=config)
    assert result == "Value: [REDACTED]"


def test_redaction_config_defaults() -> None:
    """Ensure RedactionConfig has sensible defaults."""
    config = RedactionConfig()
    assert config.patterns == []
    assert config.env_var_names == []


def test_multiple_secrets_in_one_string() -> None:
    """Ensure multiple secrets in one string are all redacted."""
    redactor = Redactor(
        patterns=DEFAULT_PATTERNS,
        literal_values=["literal-secret"],
    )

    text = (
        "Key: sk-abcdefghij1234567890 and literal-secret "
        "and Bearer xyz123abc456def789ghi012"
    )
    result = redactor.redact(text)

    assert "sk-abcdefghij1234567890" not in result
    assert "literal-secret" not in result
    assert "xyz123abc456def789ghi012" not in result
    assert result.count("[REDACTED]") == 3


def test_no_false_positive_on_short_strings() -> None:
    """Ensure short strings that look vaguely like secrets are not redacted."""
    redactor = Redactor(patterns=DEFAULT_PATTERNS, literal_values=[])

    # These should NOT be redacted (too short or not matching patterns)
    safe_strings = [
        "sk-short",
        "Bearer xyz",
        "key=value",
        "abc123",
        "RENTL_API_KEY",
        "MY_ENV_VAR",
    ]

    for safe in safe_strings:
        result = redactor.redact(safe)
        assert result == safe, f"False positive: '{safe}' was redacted"


def test_redactor_dict_with_nested_list_of_dicts() -> None:
    """Ensure redact_dict recurses into dicts inside lists."""
    redactor = Redactor(patterns=[], literal_values=["secret123"])

    data = {
        "items": [
            {"nested": "secret123", "safe": "ok"},
            {"another": "secret123"},
            "plain string secret123",
        ],
        "count": 3,
    }
    result = redactor.redact_dict(data)

    # Type assertions to help the type checker
    items = result["items"]
    assert isinstance(items, list)
    assert isinstance(items[0], dict)
    assert isinstance(items[1], dict)
    assert isinstance(items[2], str)

    assert items[0]["nested"] == "[REDACTED]"
    assert items[0]["safe"] == "ok"
    assert items[1]["another"] == "[REDACTED]"
    assert items[2] == "plain string [REDACTED]"
    assert result["count"] == 3


def test_redactor_list_with_nested_lists() -> None:
    """Ensure _redact_list handles nested lists correctly."""
    redactor = Redactor(patterns=[], literal_values=["secret123"])

    data = {
        "nested_lists": [
            ["normal", "secret123"],
            ["also normal", ["deeply nested", "secret123"]],
            42,
        ]
    }
    result = redactor.redact_dict(data)

    nested_lists = result["nested_lists"]
    assert isinstance(nested_lists, list)
    assert nested_lists[0] == ["normal", "[REDACTED]"]
    assert nested_lists[1][0] == "also normal"
    assert nested_lists[1][1] == ["deeply nested", "[REDACTED]"]
    assert nested_lists[2] == 42
