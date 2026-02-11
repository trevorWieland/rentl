"""BDD integration tests for end-to-end onboarding flow.

This test exercises the full init -> doctor -> run-pipeline -> export flow
to verify that a new user can complete the onboarding without manual edits.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_agents.runtime import ProfileAgent
from rentl_schemas.phases import (
    IdiomAnnotation,
    IdiomAnnotationList,
    SceneSummary,
    StyleGuideReviewLine,
    StyleGuideReviewList,
    TranslationResultLine,
    TranslationResultList,
)
from tests.integration.conftest import FakeLlmRuntime

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/cli/onboarding_e2e.feature")


class OnboardingContext:
    """Context object for onboarding E2E scenarios."""

    project_dir: Path | None = None
    config_path: Path | None = None
    init_result: Result | None = None
    doctor_result: Result | None = None
    pipeline_result: Result | None = None
    export_result: Result | None = None
    pipeline_response: dict | None = None
    export_response: dict | None = None


@given("a clean temporary directory", target_fixture="ctx")
def given_clean_temp_directory(tmp_path: Path) -> OnboardingContext:
    """Create a clean temporary directory for the onboarding test.

    Returns:
        OnboardingContext with project directory set.
    """
    ctx = OnboardingContext()
    ctx.project_dir = tmp_path / "onboarding-test"
    ctx.project_dir.mkdir()
    ctx.config_path = ctx.project_dir / "rentl.toml"
    return ctx


@when("I run init with preset provider selection")
def when_run_init_with_preset(
    ctx: OnboardingContext,
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run rentl init with a preset provider selection.

    Uses OpenRouter preset (option 1) with automated input.
    """
    assert ctx.project_dir is not None

    # Automated input for init command:
    # 1. Project name: onboarding-test
    # 2. Game name: Test Game
    # 3. Source language: ja
    # 4. Target languages: en
    # 5. Provider choice: 1 (OpenRouter preset)
    # 6. Model ID: (use preset default)
    # 7. Input format: jsonl
    # 8. Include seed data: y
    init_input = (
        "\n".join([
            "onboarding-test",  # project name
            "Test Game",  # game name
            "ja",  # source language
            "en",  # target languages
            "1",  # provider choice (OpenRouter preset)
            "",  # model_id (accept default)
            "jsonl",  # input format
            "y",  # include seed data
        ])
        + "\n"
    )

    # Change working directory to project_dir before running init
    # (init creates rentl.toml in Path.cwd())
    monkeypatch.chdir(ctx.project_dir)

    ctx.init_result = cli_runner.invoke(
        cli_main.app,
        ["init"],
        input=init_input,
    )


@when("I run doctor in the project directory")
def when_run_doctor(
    ctx: OnboardingContext,
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    mock_llm_runtime: FakeLlmRuntime,
) -> None:
    """Run rentl doctor with the generated config.

    Sets required API key in .env file before running doctor.
    """
    assert ctx.project_dir is not None
    assert ctx.config_path is not None

    # Create .env file with the API key that the preset expects
    # OpenRouter preset uses OPENROUTER_API_KEY
    env_path = ctx.project_dir / ".env"
    env_path.write_text("OPENROUTER_API_KEY=fake-api-key-for-e2e-test\n")

    ctx.doctor_result = cli_runner.invoke(
        cli_main.app,
        ["doctor", "--config", str(ctx.config_path)],
    )


@when("I run the pipeline with the generated config")
def when_run_pipeline(
    ctx: OnboardingContext,
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run rentl run-pipeline with the generated config.

    Uses mocked agent execution to avoid real LLM calls.
    """
    assert ctx.config_path is not None
    assert ctx.project_dir is not None

    # Track mock invocations
    mock_call_count = {"count": 0}
    edit_line_index = {"index": 0}

    # Mock ProfileAgent.run() to return deterministic schema-valid outputs
    async def mock_agent_run(self: ProfileAgent, payload: object) -> object:
        """Return schema-valid output based on agent's output_type.

        Args:
            self: ProfileAgent instance (patched method).
            payload: Input payload for the agent (phase-specific schema).

        Returns:
            Schema-valid output matching the agent's output_type.

        Raises:
            ValueError: If the agent's output_type is unexpected.
        """
        await asyncio.sleep(0)
        mock_call_count["count"] += 1

        output_type = self._output_type

        if output_type == SceneSummary:
            scene_id = getattr(payload, "scene_id", "scene_001")
            return SceneSummary(
                scene_id=scene_id,
                summary="Test scene summary from E2E mock agent",
                characters=["Character A", "Character B"],
            )
        elif output_type == IdiomAnnotationList:
            source_lines = getattr(payload, "source_lines", [])
            idioms = [
                IdiomAnnotation(
                    line_id=line.line_id,
                    idiom_text="test idiom",
                    explanation="Test explanation",
                )
                for line in source_lines[:1]
            ]
            return IdiomAnnotationList(idioms=idioms)
        elif output_type == TranslationResultList:
            source_lines = getattr(payload, "source_lines", [])
            if not source_lines:
                translations = [
                    TranslationResultLine(
                        line_id="line_001",
                        text="Test translation",
                    )
                ]
            else:
                translations = [
                    TranslationResultLine(
                        line_id=line.line_id,
                        text=f"E2E test translation for {line.line_id}",
                    )
                    for line in source_lines
                ]
            return TranslationResultList(translations=translations)
        elif output_type == StyleGuideReviewList:
            translation_results = getattr(payload, "translation_results", [])
            reviews = [
                StyleGuideReviewLine(
                    line_id=result.line_id,
                    violations=[],
                )
                for result in translation_results
            ]
            return StyleGuideReviewList(reviews=reviews)
        elif output_type == TranslationResultLine:
            translated_lines = getattr(payload, "translated_lines", [])
            if not translated_lines:
                line_id = getattr(payload, "line_id", "line_001")
            else:
                current_index = edit_line_index["index"] % len(translated_lines)
                line_id = translated_lines[current_index].line_id
                edit_line_index["index"] += 1

            return TranslationResultLine(
                line_id=line_id,
                text="Final E2E edited translation",
            )
        else:
            raise ValueError(f"Unexpected output type in E2E test mock: {output_type}")

    monkeypatch.setattr(ProfileAgent, "run", mock_agent_run)

    # Run the pipeline
    ctx.pipeline_result = cli_runner.invoke(
        cli_main.app,
        ["run-pipeline", "--config", str(ctx.config_path)],
    )

    # Parse response if available
    if ctx.pipeline_result.stdout:
        with contextlib.suppress(json.JSONDecodeError):
            # If JSON parsing fails, leave response as None
            ctx.pipeline_response = json.loads(ctx.pipeline_result.stdout)


@when("I run export for the pipeline output")
def when_run_export(
    ctx: OnboardingContext,
    cli_runner: CliRunner,
) -> None:
    """Run rentl export for the pipeline output.

    Exports the latest run to the configured output directory.
    """
    assert ctx.config_path is not None
    assert ctx.project_dir is not None

    # Find the latest run directory
    output_dir = ctx.project_dir / "out"
    if not output_dir.exists():
        # If output directory doesn't exist, export will fail
        # Run export anyway to capture the failure
        ctx.export_result = cli_runner.invoke(
            cli_main.app,
            ["export", "--config", str(ctx.config_path)],
        )
        return

    # Find run directories
    run_dirs = sorted(output_dir.glob("run-*"))
    if not run_dirs:
        # If no run directories, export will fail
        ctx.export_result = cli_runner.invoke(
            cli_main.app,
            ["export", "--config", str(ctx.config_path)],
        )
        return

    # Get the latest run directory
    latest_run_dir = run_dirs[-1]
    run_id = latest_run_dir.name.replace("run-", "")

    # Run export for the latest run
    ctx.export_result = cli_runner.invoke(
        cli_main.app,
        [
            "export",
            "--config",
            str(ctx.config_path),
            "--run-id",
            run_id,
            "--target-language",
            "en",
        ],
    )

    # Parse response if available
    if ctx.export_result.stdout:
        with contextlib.suppress(json.JSONDecodeError):
            ctx.export_response = json.loads(ctx.export_result.stdout)


@then("all commands succeed")
def then_all_commands_succeed(ctx: OnboardingContext) -> None:
    """Assert all onboarding commands succeeded.

    Verifies that init, doctor, run-pipeline, and export all completed
    successfully with exit code 0.
    """
    assert ctx.init_result is not None, "Init command was not run"
    assert ctx.init_result.exit_code == 0, (
        f"Init command failed with exit code {ctx.init_result.exit_code}\n"
        f"Output: {ctx.init_result.stdout}\n"
        f"Error: {ctx.init_result.stderr}"
    )

    assert ctx.doctor_result is not None, "Doctor command was not run"
    assert ctx.doctor_result.exit_code == 0, (
        f"Doctor command failed with exit code {ctx.doctor_result.exit_code}\n"
        f"Output: {ctx.doctor_result.stdout}\n"
        f"Error: {ctx.doctor_result.stderr}"
    )

    assert ctx.pipeline_result is not None, "Pipeline command was not run"
    assert ctx.pipeline_result.exit_code == 0, (
        f"Pipeline command failed with exit code {ctx.pipeline_result.exit_code}\n"
        f"Output: {ctx.pipeline_result.stdout}\n"
        f"Error: {ctx.pipeline_result.stderr}"
    )

    assert ctx.export_result is not None, "Export command was not run"
    assert ctx.export_result.exit_code == 0, (
        f"Export command failed with exit code {ctx.export_result.exit_code}\n"
        f"Output: {ctx.export_result.stdout}\n"
        f"Error: {ctx.export_result.stderr}"
    )


@then("the export produces output files")
def then_export_produces_output_files(ctx: OnboardingContext) -> None:
    """Assert export produced output files in the expected location.

    Verifies that the export command created output files for the
    target language in the run-specific output directory.
    """
    assert ctx.project_dir is not None
    assert ctx.pipeline_response is not None, "Pipeline response not available"

    # Get the run ID from the pipeline response
    run_id = ctx.pipeline_response.get("data", {}).get("run_id")
    assert run_id is not None, "Pipeline response missing run_id"

    # Verify export output file exists
    output_dir = ctx.project_dir / "out" / f"run-{run_id}"
    assert output_dir.exists(), f"Output directory not found: {output_dir}"

    # Check for exported file (target language: en, format: jsonl)
    export_file = output_dir / "en.jsonl"
    assert export_file.exists(), (
        f"Export file not found: {export_file}\n"
        f"Output directory contents: {list(output_dir.glob('*'))}"
    )

    # Verify export file is not empty
    content = export_file.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, f"Export file is empty: {export_file}"


@then("no manual edits were required")
def then_no_manual_edits_required(ctx: OnboardingContext) -> None:
    """Assert no manual edits were required between steps.

    This is a meta-assertion that verifies the flow succeeded without
    any manual intervention. If all previous assertions pass, this is
    satisfied by definition.
    """
    # This assertion is satisfied if all commands succeeded
    # and the export produced output files
    assert ctx.init_result is not None
    assert ctx.doctor_result is not None
    assert ctx.pipeline_result is not None
    assert ctx.export_result is not None
    assert ctx.init_result.exit_code == 0
    assert ctx.doctor_result.exit_code == 0
    assert ctx.pipeline_result.exit_code == 0
    assert ctx.export_result.exit_code == 0
