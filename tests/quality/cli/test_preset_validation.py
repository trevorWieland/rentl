"""Quality tests for provider preset validation against live APIs.

These tests validate that provider preset configurations (base URL, model ID)
work against real provider APIs. They catch preset drift before it reaches
production.

Tests marked with `@pytest.mark.quality` and `@pytest.mark.api` require valid
API keys to run and have a 30-second timeout. They can be skipped if API keys
are not available in the environment.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

import rentl.main as cli_main
from rentl_core.init import ENDPOINT_PRESETS, StandardEnvVar

if TYPE_CHECKING:
    pass


@pytest.mark.quality
@pytest.mark.api
def test_openrouter_preset_validates_against_live_api(
    tmp_path: Path,
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that OpenRouter preset model ID validates against live API.

    GIVEN the OpenRouter provider preset
    WHEN I run init with OpenRouter preset
     AND I run doctor with a valid API key
    THEN doctor's LLM connectivity check passes

    This test requires RENTL_QUALITY_API_KEY in the environment.

    Args:
        tmp_path: Temporary directory for the test project.
        cli_runner: CliRunner for invoking CLI commands.
        monkeypatch: Pytest monkeypatch for setting environment variables.

    Raises:
        ValueError: If RENTL_QUALITY_API_KEY is not set.
    """
    # Require API key for quality tests
    api_key = os.environ.get("RENTL_QUALITY_API_KEY")
    if not api_key:
        raise ValueError("RENTL_QUALITY_API_KEY must be set for quality tests")

    # Create a project directory
    project_dir = tmp_path / "preset-validation-test"
    project_dir.mkdir()
    config_path = project_dir / "rentl.toml"

    # Automated input for init command using OpenRouter preset
    init_input = (
        "\n".join([
            "preset-validation-test",  # project name
            "Preset Test Game",  # game name
            "ja",  # source language
            "en",  # target languages
            "1",  # endpoint choice (OpenRouter preset)
            "jsonl",  # input format
            "y",  # include seed data
        ])
        + "\n"
    )

    # Change working directory to project_dir before running init
    monkeypatch.chdir(project_dir)

    # Run init with OpenRouter preset
    init_result = cli_runner.invoke(
        cli_main.app,
        ["init"],
        input=init_input,
    )

    # Assert init succeeded
    assert init_result.exit_code == 0, (
        f"Init failed with exit code {init_result.exit_code}\n"
        f"Output: {init_result.stdout}\n"
        f"Error: {init_result.stderr}"
    )

    # Verify config was created
    assert config_path.exists(), f"Config file not created: {config_path}"

    # Verify .env was created by init
    env_path = project_dir / ".env"
    assert env_path.exists(), f".env file not created by init: {env_path}"

    # Run doctor with the generated config, injecting API key via environment
    doctor_result = cli_runner.invoke(
        cli_main.app,
        ["doctor", "--config", str(config_path)],
        env={StandardEnvVar.API_KEY.value: api_key},
    )

    # Assert doctor succeeded
    assert doctor_result.exit_code == 0, (
        f"Doctor failed with exit code {doctor_result.exit_code}\n"
        f"Output: {doctor_result.stdout}\n"
        f"Error: {doctor_result.stderr}\n"
        f"\n"
        f"This indicates the OpenRouter preset's model ID is invalid or "
        f"unreachable. Check the preset configuration in "
        f"packages/rentl-core/src/rentl_core/init.py and verify the model ID "
        f"exists on OpenRouter."
    )

    # Verify that doctor output contains passing LLM connectivity check
    doctor_output = doctor_result.stdout
    assert "LLM Connectivity" in doctor_output, (
        f"Doctor output missing LLM connectivity check:\n{doctor_output}"
    )

    # The doctor output should contain "PASS" for the connectivity check
    # or at least not contain "FAIL"
    assert "FAIL" not in doctor_output or "0/1 endpoint(s) failed" in doctor_output, (
        f"Doctor reported LLM connectivity failure:\n{doctor_output}\n"
        f"\n"
        f"OpenRouter preset configuration:\n"
        f"  Model ID: {ENDPOINT_PRESETS[0].default_model}\n"
        f"  Base URL: {ENDPOINT_PRESETS[0].base_url}\n"
    )


def test_all_presets_have_valid_structure(
    cli_runner: CliRunner,
) -> None:
    """Test that all endpoint presets have valid structure.

    GIVEN the list of ENDPOINT_PRESETS
    WHEN I inspect each preset
    THEN each preset has required fields populated

    This is a structural validation test that does not require API keys.
    It ensures presets have non-empty values for all required fields.

    Args:
        cli_runner: CliRunner (unused, but required for test signature consistency).
    """
    assert len(ENDPOINT_PRESETS) >= 3, (
        "Spec requires at least 3 endpoint presets (OpenRouter, OpenAI, Local/Ollama)"
    )

    required_preset_names = {"OpenRouter", "OpenAI", "Local (Ollama)"}
    available_preset_names = {preset.name for preset in ENDPOINT_PRESETS}

    assert required_preset_names.issubset(available_preset_names), (
        f"Missing required presets. Expected: {required_preset_names}, "
        f"Got: {available_preset_names}"
    )

    for preset in ENDPOINT_PRESETS:
        # Verify all fields are populated
        assert preset.name, f"Preset missing name: {preset}"
        assert preset.base_url, f"Preset {preset.name} missing base_url"
        assert preset.default_model, f"Preset {preset.name} missing default_model"

        # Verify base_url is a valid URL format
        assert preset.base_url.startswith("http"), (
            f"Preset {preset.name} has invalid base_url: {preset.base_url}"
        )
