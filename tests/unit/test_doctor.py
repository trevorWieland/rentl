"""Tests for the doctor/onboarding CLI command."""

from __future__ import annotations

import contextlib
from pathlib import Path

from rentl_cli.main import app
from rentl_core.config.settings import get_settings
from typer.testing import CliRunner

runner = CliRunner()


def _reset_settings_cache() -> None:
    with contextlib.suppress(Exception):
        get_settings.cache_clear()


def test_doctor_passes_with_env(tmp_path: Path) -> None:
    """Doctor should succeed when required env vars are present."""
    _reset_settings_cache()
    result = runner.invoke(
        app,
        ["doctor", "--project-path", "examples/tiny_vn", "--verbosity", "info", "--skip-status"],
        env={
            "OPENAI_URL": "http://localhost:1234/v1",
            "OPENAI_API_KEY": "dummy",
            "LLM_MODEL": "dummy-model",
        },
    )
    assert result.exit_code == 0
    assert "LLM config: OK" in result.stdout
    assert "Project loaded:" in result.stdout


def test_doctor_fails_when_env_missing(tmp_path: Path) -> None:
    """Doctor should fail when required env vars are missing."""
    _reset_settings_cache()
    result = runner.invoke(
        app,
        ["doctor", "--project-path", "examples/tiny_vn", "--verbosity", "info", "--skip-status"],
        env={
            "OPENAI_URL": "http://localhost:1234/v1",
            "OPENAI_API_KEY": "",
            "LLM_MODEL": "",
        },
    )
    assert result.exit_code != 0
    assert "missing required environment variables" in result.stdout or "missing" in result.stdout
