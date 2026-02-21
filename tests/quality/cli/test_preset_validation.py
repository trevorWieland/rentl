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
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main
from rentl_core.init import ENDPOINT_PRESETS, StandardEnvVar
from rentl_schemas.config import RunConfig

if TYPE_CHECKING:
    pass

scenarios("../features/cli/preset_validation.feature")


class PresetValidationContext:
    """Test context for preset validation BDD scenarios."""

    project_dir: Path | None = None
    config_path: Path | None = None
    api_key: str | None = None
    init_result: Result | None = None
    doctor_result: Result | None = None


# ---------------------------------------------------------------------------
# Scenario: OpenRouter preset validates against live API
# ---------------------------------------------------------------------------


@pytest.fixture
def ctx() -> PresetValidationContext:
    """Create test context.

    Returns:
        PresetValidationContext: Empty context for BDD scenarios.
    """
    return PresetValidationContext()


@given("the OpenRouter provider preset", target_fixture="ctx")
def given_openrouter_preset() -> PresetValidationContext:
    """Verify OpenRouter preset exists and API key is available.

    Returns:
        PresetValidationContext with API key loaded.

    Raises:
        ValueError: If RENTL_QUALITY_API_KEY is not set.
    """
    ctx = PresetValidationContext()
    api_key = os.environ.get("RENTL_QUALITY_API_KEY")
    if not api_key:
        raise ValueError("RENTL_QUALITY_API_KEY must be set for quality tests")
    ctx.api_key = api_key
    return ctx


@given("a fresh project initialized with OpenRouter preset")
def given_fresh_project(
    ctx: PresetValidationContext,
    tmp_path: Path,
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Initialize a fresh project with the OpenRouter preset."""
    ctx.project_dir = tmp_path / "preset-validation-test"
    ctx.project_dir.mkdir()
    ctx.config_path = ctx.project_dir / "rentl.toml"

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

    monkeypatch.chdir(ctx.project_dir)

    ctx.init_result = cli_runner.invoke(
        cli_main.app,
        ["init"],
        input=init_input,
    )

    assert ctx.init_result.exit_code == 0, (
        f"Init failed with exit code {ctx.init_result.exit_code}\n"
        f"Output: {ctx.init_result.stdout}\n"
        f"Error: {ctx.init_result.stderr}"
    )

    assert ctx.config_path.exists(), f"Config file not created: {ctx.config_path}"
    with ctx.config_path.open("rb") as f:
        RunConfig.model_validate(tomllib.load(f))

    env_path = ctx.project_dir / ".env"
    assert env_path.exists(), f".env file not created by init: {env_path}"


@when("I run doctor with a valid API key")
def when_run_doctor(
    ctx: PresetValidationContext,
    cli_runner: CliRunner,
) -> None:
    """Run doctor with the generated config and valid API key."""
    assert ctx.config_path is not None
    assert ctx.api_key is not None

    ctx.doctor_result = cli_runner.invoke(
        cli_main.app,
        ["doctor", "--config", str(ctx.config_path)],
        env={StandardEnvVar.API_KEY.value: ctx.api_key},
    )


@then("doctor completes successfully")
def then_doctor_succeeds(ctx: PresetValidationContext) -> None:
    """Assert doctor exited with code 0."""
    assert ctx.doctor_result is not None
    assert ctx.doctor_result.exit_code == 0, (
        f"Doctor failed with exit code {ctx.doctor_result.exit_code}\n"
        f"Output: {ctx.doctor_result.stdout}\n"
        f"Error: {ctx.doctor_result.stderr}\n"
        f"\n"
        f"This indicates the OpenRouter preset's model ID is invalid or "
        f"unreachable. Check the preset configuration in "
        f"packages/rentl-core/src/rentl_core/init.py and verify the model ID "
        f"exists on OpenRouter."
    )


@then("the LLM connectivity check passes")
def then_llm_connectivity_passes(ctx: PresetValidationContext) -> None:
    """Assert doctor output shows passing LLM connectivity."""
    assert ctx.doctor_result is not None
    doctor_output = ctx.doctor_result.stdout

    assert "LLM Connectivity" in doctor_output, (
        f"Doctor output missing LLM connectivity check:\n{doctor_output}"
    )

    assert "FAIL" not in doctor_output or "0/1 endpoint(s) failed" in doctor_output, (
        f"Doctor reported LLM connectivity failure:\n{doctor_output}\n"
        f"\n"
        f"OpenRouter preset configuration:\n"
        f"  Model ID: {ENDPOINT_PRESETS[0].default_model}\n"
        f"  Base URL: {ENDPOINT_PRESETS[0].base_url}\n"
    )


# ---------------------------------------------------------------------------
# Scenario: All presets have valid structure
# ---------------------------------------------------------------------------


@given("the list of endpoint presets", target_fixture="ctx")
def given_endpoint_presets() -> PresetValidationContext:
    """Load endpoint presets for structural validation.

    Returns:
        PresetValidationContext (no API key needed for structural checks).
    """
    return PresetValidationContext()


@then("all required presets are present")
def then_required_presets_present(ctx: PresetValidationContext) -> None:
    """Assert all required preset names exist."""
    assert len(ENDPOINT_PRESETS) >= 3, (
        "Spec requires at least 3 endpoint presets (OpenRouter, OpenAI, Local)"
    )

    required_preset_names = {"OpenRouter", "OpenAI", "Local"}
    available_preset_names = {preset.name for preset in ENDPOINT_PRESETS}

    assert required_preset_names.issubset(available_preset_names), (
        f"Missing required presets. Expected: {required_preset_names}, "
        f"Got: {available_preset_names}"
    )


@then("each preset has required fields populated")
def then_presets_have_fields(ctx: PresetValidationContext) -> None:
    """Assert each preset has all required fields with valid values."""
    for preset in ENDPOINT_PRESETS:
        assert preset.name, f"Preset missing name: {preset}"
        assert preset.base_url, f"Preset {preset.name} missing base_url"

        if preset.name != "Local":
            assert preset.default_model, f"Preset {preset.name} missing default_model"
        else:
            assert preset.default_model is None, (
                f"Local preset must have default_model=None, "
                f"got: {preset.default_model}"
            )

        assert preset.base_url.startswith("http"), (
            f"Preset {preset.name} has invalid base_url: {preset.base_url}"
        )
