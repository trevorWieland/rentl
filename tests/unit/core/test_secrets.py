"""Unit tests for secret-scanning validation logic."""

from __future__ import annotations

from pathlib import Path

from rentl_core.secrets import check_config_secrets, looks_like_secret


class TestLooksLikeSecret:
    """Test suite for looks_like_secret function."""

    def test_env_var_name_not_secret(self) -> None:
        """Uppercase env var names with underscores are not secrets."""
        assert looks_like_secret("RENTL_OPENROUTER_API_KEY") is False
        assert looks_like_secret("OPENAI_API_KEY") is False
        assert looks_like_secret("MY_SECRET_TOKEN") is False

    def test_openai_key_pattern_detected(self) -> None:
        """OpenAI-style sk-* keys are detected as secrets."""
        assert looks_like_secret("sk-abcdefghijklmnopqrstuvwxyz") is True

    def test_bearer_token_detected(self) -> None:
        """Bearer tokens are detected as secrets."""
        assert looks_like_secret("Bearer abcdefghijklmnopqrstuvwxyz") is True

    def test_empty_string_not_secret(self) -> None:
        """Empty string is not a secret."""
        assert looks_like_secret("") is False

    def test_short_string_not_secret(self) -> None:
        """Short strings that don't match patterns are not secrets."""
        assert looks_like_secret("hello") is False


class TestCheckConfigSecrets:
    """Test suite for check_config_secrets function."""

    def test_clean_config_no_findings(self, tmp_path: Path) -> None:
        """Clean config with env var names returns no findings."""
        config_data = {
            "endpoint": {"api_key_env": "RENTL_OPENROUTER_API_KEY"},
        }
        findings = check_config_secrets(config_data, tmp_path)
        assert findings == []

    def test_secret_in_endpoint_detected(self, tmp_path: Path) -> None:
        """Secret value in endpoint.api_key_env is detected."""
        config_data = {
            "endpoint": {"api_key_env": "sk-abcdefghijklmnopqrstuvwxyz"},
        }
        findings = check_config_secrets(config_data, tmp_path)
        assert len(findings) == 1
        assert "endpoint.api_key_env" in findings[0]

    def test_secret_in_multi_endpoint_detected(self, tmp_path: Path) -> None:
        """Secret value in multi-endpoint config is detected."""
        config_data = {
            "endpoints": {
                "endpoints": [
                    {
                        "provider_name": "openai",
                        "api_key_env": "sk-abcdefghijklmnopqrstuvwxyz",
                    },
                ],
            },
        }
        findings = check_config_secrets(config_data, tmp_path)
        assert len(findings) == 1
        assert "endpoints.endpoints[0]" in findings[0]
        assert "openai" in findings[0]

    def test_env_file_not_in_gitignore(self, tmp_path: Path) -> None:
        """Warns when .env exists but is not in .gitignore."""
        (tmp_path / ".env").write_text("SECRET=value\n")
        # No .gitignore at all
        findings = check_config_secrets({}, tmp_path)
        assert len(findings) == 1
        assert ".gitignore" in findings[0]

    def test_env_file_in_gitignore_clean(self, tmp_path: Path) -> None:
        """No finding when .env exists and is in .gitignore (non-git repo)."""
        (tmp_path / ".env").write_text("SECRET=value\n")
        (tmp_path / ".gitignore").write_text(".env\n")
        findings = check_config_secrets({}, tmp_path)
        assert findings == []

    def test_no_env_file_clean(self, tmp_path: Path) -> None:
        """No finding when .env does not exist."""
        findings = check_config_secrets({}, tmp_path)
        assert findings == []

    def test_empty_config_no_findings(self, tmp_path: Path) -> None:
        """Empty config dict returns no findings."""
        findings = check_config_secrets({}, tmp_path)
        assert findings == []
