"""Unit tests for check-secrets CLI command."""

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from rentl_cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner.

    Returns:
        CliRunner: Test runner for invoking CLI commands.
    """
    return CliRunner()


def test_check_secrets_clean_config(runner: CliRunner, tmp_path: Path) -> None:
    """Test check-secrets with a clean config (env var names)."""
    config_file = tmp_path / "rentl.toml"
    config_file.write_text(
        dedent(
            """
            [project]
            schema_version = { major = 0, minor = 1, patch = 0 }
            project_name = "test"

            [endpoint]
            provider_name = "openrouter"
            base_url = "https://openrouter.ai/api/v1"
            api_key_env = "RENTL_OPENROUTER_API_KEY"
            timeout_s = 180
            """
        )
    )

    result = runner.invoke(app, ["check-secrets", "--config", str(config_file)])

    assert result.exit_code == 0
    assert "PASS" in result.stdout or "No hardcoded secrets detected" in result.stdout


def test_check_secrets_hardcoded_api_key(runner: CliRunner, tmp_path: Path) -> None:
    """Test check-secrets detects hardcoded API key."""
    config_file = tmp_path / "rentl.toml"
    config_file.write_text(
        dedent(
            """
            [project]
            schema_version = { major = 0, minor = 1, patch = 0 }
            project_name = "test"

            [endpoint]
            provider_name = "openrouter"
            base_url = "https://openrouter.ai/api/v1"
            api_key_env = "sk-1234567890abcdefghijklmnop"
            timeout_s = 180
            """
        )
    )

    result = runner.invoke(app, ["check-secrets", "--config", str(config_file)])

    assert result.exit_code == 1  # Findings detected
    assert "endpoint.api_key_env contains what looks like a secret" in result.stdout


def test_check_secrets_env_file_not_in_gitignore(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Test check-secrets warns about .env file not in .gitignore."""
    config_file = tmp_path / "rentl.toml"
    config_file.write_text(
        dedent(
            """
            [project]
            schema_version = { major = 0, minor = 1, patch = 0 }
            project_name = "test"

            [endpoint]
            provider_name = "openrouter"
            base_url = "https://openrouter.ai/api/v1"
            api_key_env = "RENTL_OPENROUTER_API_KEY"
            timeout_s = 180
            """
        )
    )

    # Create .env file but no .gitignore
    env_file = tmp_path / ".env"
    env_file.write_text("RENTL_OPENROUTER_API_KEY=secret123\n")

    result = runner.invoke(app, ["check-secrets", "--config", str(config_file)])

    assert result.exit_code == 1  # Findings detected
    assert ".env file exists" in result.stdout
    assert ".gitignore" in result.stdout


def test_check_secrets_env_file_in_gitignore(runner: CliRunner, tmp_path: Path) -> None:
    """Test check-secrets passes when .env is in .gitignore."""
    config_file = tmp_path / "rentl.toml"
    config_file.write_text(
        dedent(
            """
            [project]
            schema_version = { major = 0, minor = 1, patch = 0 }
            project_name = "test"

            [endpoint]
            provider_name = "openrouter"
            base_url = "https://openrouter.ai/api/v1"
            api_key_env = "RENTL_OPENROUTER_API_KEY"
            timeout_s = 180
            """
        )
    )

    # Create .env file and .gitignore with .env entry
    env_file = tmp_path / ".env"
    env_file.write_text("RENTL_OPENROUTER_API_KEY=secret123\n")

    gitignore_file = tmp_path / ".gitignore"
    gitignore_file.write_text("*.pyc\n.env\n__pycache__/\n")

    result = runner.invoke(app, ["check-secrets", "--config", str(config_file)])

    assert result.exit_code == 0
    assert "PASS" in result.stdout or "No hardcoded secrets detected" in result.stdout


def test_check_secrets_nonexistent_config(runner: CliRunner, tmp_path: Path) -> None:
    """Test check-secrets with nonexistent config file."""
    config_file = tmp_path / "nonexistent.toml"

    result = runner.invoke(app, ["check-secrets", "--config", str(config_file)])

    assert result.exit_code == 11  # VALIDATION_ERROR (not a finding, but an error)
    assert "Config file not found" in result.stdout


def test_check_secrets_invalid_toml(runner: CliRunner, tmp_path: Path) -> None:
    """Test check-secrets with invalid TOML syntax."""
    config_file = tmp_path / "rentl.toml"
    config_file.write_text("this is not valid TOML {{{\n")

    result = runner.invoke(app, ["check-secrets", "--config", str(config_file)])

    assert result.exit_code == 11  # VALIDATION_ERROR (not a finding, but an error)
    assert "Failed to parse config" in result.stdout


def test_check_secrets_bearer_token_pattern(runner: CliRunner, tmp_path: Path) -> None:
    """Test check-secrets detects Bearer token pattern."""
    config_file = tmp_path / "rentl.toml"
    config_file.write_text(
        dedent(
            """
            [project]
            schema_version = { major = 0, minor = 1, patch = 0 }
            project_name = "test"

            [endpoint]
            provider_name = "openrouter"
            base_url = "https://openrouter.ai/api/v1"
            api_key_env = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            timeout_s = 180
            """
        )
    )

    result = runner.invoke(app, ["check-secrets", "--config", str(config_file)])

    assert result.exit_code == 1  # Findings detected
    assert "endpoint.api_key_env contains what looks like a secret" in result.stdout


def test_check_secrets_git_repo_untracked_env_no_gitignore_rule(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Regression: git repo with untracked .env and no .gitignore rule fails."""
    config_file = tmp_path / "rentl.toml"
    config_file.write_text(
        dedent(
            """
            [project]
            schema_version = { major = 0, minor = 1, patch = 0 }
            project_name = "test"

            [endpoint]
            provider_name = "openrouter"
            base_url = "https://openrouter.ai/api/v1"
            api_key_env = "RENTL_OPENROUTER_API_KEY"
            timeout_s = 180
            """
        )
    )

    # Create .env file
    env_file = tmp_path / ".env"
    env_file.write_text("RENTL_OPENROUTER_API_KEY=secret123\n")

    # Initialize git repo (don't add or commit .env)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "rentl.toml"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # .env exists, is untracked, and has no .gitignore rule — should fail
    result = runner.invoke(app, ["check-secrets", "--config", str(config_file)])

    assert result.exit_code == 1  # Findings detected
    assert ".env file exists" in result.stdout
    assert ".gitignore" in result.stdout
