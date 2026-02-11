"""BDD integration tests for init CLI command."""

from __future__ import annotations

import asyncio
import json
import os
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_agents.runtime import ProfileAgent
from rentl_agents.wiring import build_agent_pools
from rentl_core.init import PROVIDER_PRESETS, InitAnswers, generate_project
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import (
    IdiomAnnotation,
    IdiomAnnotationList,
    SceneSummary,
    StyleGuideReviewLine,
    StyleGuideReviewList,
    TranslationResultLine,
    TranslationResultList,
)
from rentl_schemas.primitives import FileFormat, JsonValue
from rentl_schemas.validation import validate_run_config
from tests.integration.conftest import FakeLlmRuntime

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/cli/init.feature")


class InitContext:
    """Context object for init BDD scenarios."""

    target_dir: Path | None = None
    answers: InitAnswers | None = None
    result_created_files: list[str] | None = None
    config_path: Path | None = None


@given("an empty temp directory", target_fixture="ctx")
def given_empty_temp_directory(tmp_path: Path) -> InitContext:
    """Create an empty temporary directory for the project.

    Returns:
        InitContext with target directory set.
    """
    ctx = InitContext()
    ctx.target_dir = tmp_path / "test-project"
    ctx.target_dir.mkdir()
    return ctx


@when("I generate a project with default answers")
def when_generate_project_with_defaults(ctx: InitContext) -> None:
    """Run generate_project with default answers."""
    assert ctx.target_dir is not None

    # Create default answers matching the CLI defaults
    ctx.answers = InitAnswers(
        project_name="test-project",
        game_name="Test Game",
        source_language="ja",
        target_languages=["en"],
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_id="openai/gpt-4-turbo",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    # Generate the project
    result = generate_project(ctx.answers, ctx.target_dir)
    ctx.result_created_files = result.created_files
    ctx.config_path = ctx.target_dir / "rentl.toml"


@then("the command succeeds")
def then_command_succeeds(ctx: InitContext) -> None:
    """Assert the project generation succeeded."""
    # For direct core function calls, success is implicit - no exception raised
    assert ctx.result_created_files is not None
    assert len(ctx.result_created_files) > 0


@then("all expected files exist")
def then_all_expected_files_exist(ctx: InitContext) -> None:
    """Assert all expected files and directories were created."""
    assert ctx.target_dir is not None
    assert ctx.config_path is not None
    assert ctx.answers is not None, "InitAnswers should be set by this step"

    # Check that all expected files exist
    expected_files = [
        ctx.target_dir / "rentl.toml",
        ctx.target_dir / ".env",
        ctx.target_dir / "input",
        ctx.target_dir / "out",
        ctx.target_dir / "logs",
        ctx.target_dir / "input" / f"{ctx.answers.game_name}.jsonl",
    ]

    for path in expected_files:
        assert path.exists(), f"Expected file/directory does not exist: {path}"


@then("the generated config validates")
def then_generated_config_validates(ctx: InitContext) -> None:
    """Assert the generated rentl.toml passes validation.

    Raises:
        AssertionError: If validation fails.
    """
    assert ctx.config_path is not None
    assert ctx.config_path.exists()

    # Parse TOML
    with ctx.config_path.open("rb") as handle:
        payload: dict[str, JsonValue] = tomllib.load(handle)

    # Validate against RunConfig schema
    try:
        config = validate_run_config(payload)
        assert config is not None
    except Exception as exc:
        raise AssertionError(
            f"Generated config failed validation: {exc}\nPayload: {payload}"
        ) from exc


@then("the generated config resolves without errors")
def then_generated_config_resolves(ctx: InitContext) -> None:
    """Assert the generated config can be resolved (path resolution)."""
    assert ctx.config_path is not None
    assert ctx.target_dir is not None

    # Parse and validate TOML
    with ctx.config_path.open("rb") as handle:
        payload: dict[str, JsonValue] = tomllib.load(handle)

    config = validate_run_config(payload)

    # Resolve project paths (mimics CLI _resolve_project_paths logic)
    workspace_dir = Path(config.project.paths.workspace_dir)
    if not workspace_dir.is_absolute():
        workspace_dir = (ctx.config_path.parent / workspace_dir).resolve()

    # Verify workspace resolution doesn't raise
    assert workspace_dir.exists(), f"Workspace directory not found: {workspace_dir}"

    # Verify input/output/logs paths exist
    input_path = workspace_dir / config.project.paths.input_path
    output_dir = workspace_dir / config.project.paths.output_dir
    logs_dir = workspace_dir / config.project.paths.logs_dir

    # Input path won't exist yet (it's a file pattern), but the parent should
    assert input_path.parent.exists(), f"Input directory not found: {input_path.parent}"
    assert output_dir.exists(), f"Output directory not found: {output_dir}"
    assert logs_dir.exists(), f"Logs directory not found: {logs_dir}"


@then("the seed data file is valid JSONL")
def then_seed_data_is_valid_jsonl(ctx: InitContext) -> None:
    """Assert the seed data file contains valid JSONL with SourceLine structure.

    Raises:
        AssertionError: If validation fails.
    """
    assert ctx.target_dir is not None
    assert ctx.answers is not None

    seed_path = (
        ctx.target_dir / "input" / f"{ctx.answers.game_name}.{ctx.answers.input_format}"
    )
    assert seed_path.exists(), f"Seed data file not found: {seed_path}"

    # Read JSONL content
    content = seed_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.strip().split("\n") if line.strip()]

    # Verify we have at least one line
    assert len(lines) > 0, "Seed data file is empty"

    # Parse each line and validate against SourceLine schema
    for i, line in enumerate(lines):
        try:
            line_data = json.loads(line)
            source_line = SourceLine.model_validate(line_data)
            # Verify required fields
            assert source_line.line_id, f"Line {i} missing line_id"
            assert source_line.text, f"Line {i} missing text"
            assert source_line.scene_id, f"Line {i} missing scene_id"
        except Exception as exc:
            raise AssertionError(
                f"Seed data line {i} failed validation: {exc}\nLine: {line}"
            ) from exc

    # Verify seed data content matches configured source language
    # Default source language is "ja" so expect Japanese text
    assert "サンプル台詞" in content, (
        f"Seed data should contain Japanese text for source_language='ja', "
        f"but got: {content[:100]}"
    )


@then("the pipeline can execute end-to-end and produce export artifacts")
def then_pipeline_executes_end_to_end(
    ctx: InitContext,
    monkeypatch: pytest.MonkeyPatch,
    cli_runner: CliRunner,
    mock_llm_runtime: FakeLlmRuntime,
) -> None:
    """Assert the generated project can execute the full pipeline and exports.

    This test verifies that:
    1. Config validates and resolves
    2. Pipeline phases include required ingest and export
    3. Full pipeline execution completes successfully with mocked agents
    4. Export artifacts are produced in the expected locations

    Note on mocking strategy:
    - We patch ProfileAgent.run() which is the actual execution boundary
      used by the pipeline
    - This avoids patching internal pydantic-ai details while still
      providing deterministic results
    - Each agent returns schema-valid output matching its output_type
    """
    assert ctx.config_path is not None
    assert ctx.answers is not None
    assert ctx.target_dir is not None

    # Parse and validate TOML
    with ctx.config_path.open("rb") as handle:
        payload: dict[str, JsonValue] = tomllib.load(handle)

    config = validate_run_config(payload)

    # Set the API key environment variable that the generated config references
    # This makes the test deterministic and self-contained
    monkeypatch.setenv(ctx.answers.api_key_env, "fake-api-key-for-testing")

    # Verify pipeline has required ingest and export phases
    # Without these, the pipeline will fail at runtime
    assert config.pipeline.phases is not None
    phase_names = [phase.phase for phase in config.pipeline.phases]
    assert "ingest" in phase_names, "Pipeline missing required 'ingest' phase"
    assert "export" in phase_names, "Pipeline missing required 'export' phase"

    # Verify agent pools can be built from the generated config
    # This proves the agent references are valid and default agents resolve
    pools = build_agent_pools(config=config)
    assert pools is not None

    # Verify agent pools were created for the expected phases
    # The bundle has specific fields for each phase type
    assert len(pools.context_agents) > 0, "No context agents in pool"
    assert len(pools.pretranslation_agents) > 0, "No pretranslation agents in pool"
    assert len(pools.translate_agents) > 0, "No translate agents in pool"
    assert len(pools.qa_agents) > 0, "No QA agents in pool"
    assert len(pools.edit_agents) > 0, "No edit agents in pool"

    # Verify seed input file exists and matches configured input path
    # This ensures the generated project can start pipeline execution immediately
    input_file = (
        ctx.target_dir / "input" / f"{ctx.answers.game_name}.{ctx.answers.input_format}"
    )
    assert input_file.exists(), (
        f"Seed input file not found: {input_file}\n"
        f"Config expects: {config.project.paths.input_path}\n"
        f"This mismatch would cause pipeline execution to fail immediately"
    )

    # Track mock invocations to verify deterministic stub was used
    mock_call_count = {"count": 0}
    # Track which line index we're editing
    # (for edit phase that processes one line at a time)
    edit_line_index = {"index": 0}

    # Create mock for ProfileAgent.run() to return deterministic
    # schema-valid outputs. This is the execution boundary actually
    # used by run-pipeline via build_agent_pools()

    async def mock_agent_run(self: ProfileAgent, payload: object) -> object:
        """Return schema-valid output based on agent's output_type.

        For batch operations, returns outputs matching all input IDs to satisfy
        the pipeline's alignment requirements.

        Args:
            self: ProfileAgent instance (patched method).
            payload: Input payload for the agent (phase-specific schema).

        Returns:
            Schema-valid output matching the agent's output_type.

        Raises:
            ValueError: If the agent's output_type is unexpected.
        """
        # Make this a true async function with asyncio.sleep(0)
        await asyncio.sleep(0)

        mock_call_count["count"] += 1

        # Determine output type from the agent
        output_type = self._output_type

        # Return schema-valid output matching each agent type
        if output_type == SceneSummary:
            # Context phase: return summary for the scene
            scene_id = getattr(payload, "scene_id", "scene_001")
            return SceneSummary(
                scene_id=scene_id,
                summary="Test scene summary from mock agent",
                characters=["Character A", "Character B"],
            )
        elif output_type == IdiomAnnotationList:
            # Pretranslation phase: return idioms for batch of source lines
            source_lines = getattr(payload, "source_lines", [])
            idioms = [
                IdiomAnnotation(
                    line_id=line.line_id,
                    idiom_text="test idiom",
                    explanation="Test explanation",
                )
                for line in source_lines[:1]  # Return at least one idiom
            ]
            return IdiomAnnotationList(idioms=idioms)
        elif output_type == TranslationResultList:
            # Translation phase: return translation for each source line
            source_lines = getattr(payload, "source_lines", [])
            if not source_lines:
                # Fallback: create at least one translation
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
                        text=f"Test translation for {line.line_id}",
                    )
                    for line in source_lines
                ]
            return TranslationResultList(translations=translations)
        elif output_type == StyleGuideReviewList:
            # QA phase: return review for each translation (no violations)
            translation_results = getattr(payload, "translation_results", [])
            reviews = [
                StyleGuideReviewLine(
                    line_id=result.line_id,
                    violations=[],  # Empty list means no violations (approved)
                )
                for result in translation_results
            ]
            return StyleGuideReviewList(reviews=reviews)
        elif output_type == TranslationResultLine:
            # Edit phase: return final translation for single line
            # The agent is called once per line, but receives ALL lines in context
            # We need to cycle through the lines to match what the orchestrator expects
            translated_lines = getattr(payload, "translated_lines", [])
            if not translated_lines:
                # Fallback if no translated_lines provided
                line_id = getattr(payload, "line_id", "line_001")
            else:
                # Get the current line index and cycle through available lines
                current_index = edit_line_index["index"] % len(translated_lines)
                line_id = translated_lines[current_index].line_id
                # Increment for next call
                edit_line_index["index"] += 1

            return TranslationResultLine(
                line_id=line_id,
                text="Final edited translation",
            )
        else:
            # Fallback for any other output types
            raise ValueError(f"Unexpected output type in test mock: {output_type}")

    monkeypatch.setattr(ProfileAgent, "run", mock_agent_run)

    # Execute the full pipeline end-to-end with mocked agent execution
    result = cli_runner.invoke(
        cli_main.app,
        ["run-pipeline", "--config", str(ctx.config_path)],
    )

    # Verify the mock was actually invoked during pipeline execution
    # This proves we're using deterministic test doubles, not real LLM calls
    assert mock_call_count["count"] > 0, (
        "Mock agent execution was never called - "
        "the patch may not be at the correct execution boundary"
    )

    # Verify the pipeline completed successfully
    assert result.exit_code == 0, (
        f"Pipeline execution failed with exit code {result.exit_code}\n"
        f"Output: {result.stdout}\n"
        f"Error: {result.stderr}\n"
        f"Mock was called {mock_call_count['count']} times"
    )

    # Parse the response to verify execution succeeded
    response = json.loads(result.stdout)
    assert response.get("error") is None, (
        f"Pipeline execution returned error: {response.get('error')}"
    )
    assert response.get("data") is not None, "Pipeline response missing data"

    # Only verify export artifacts if pipeline completed successfully (exit_code == 0).
    # This gating ensures the test doesn't fail on artifact assertions if
    # execution failed.
    if result.exit_code == 0:
        # The config defines where output should be written
        expected_output_dir = config.project.paths.output_dir
        output_dir = ctx.target_dir / expected_output_dir

        assert output_dir.exists(), (
            f"Output directory not found after pipeline execution\n"
            f"Expected: {output_dir}\n"
            f"Config output_dir: {expected_output_dir}"
        )

        # The export phase creates output in a run-specific subdirectory
        # Find the run directory (there should be exactly one)
        run_dirs = list(output_dir.glob("run-*"))
        assert len(run_dirs) == 1, (
            f"Expected exactly one run directory, found {len(run_dirs)}: {run_dirs}"
        )
        run_dir = run_dirs[0]

        # Verify export artifacts were produced for each target language
        for target_lang in ctx.answers.target_languages:
            # Export file is named {lang}.{format} in the run directory
            export_file = run_dir / f"{target_lang}.{ctx.answers.input_format}"
            assert export_file.exists(), (
                f"Export artifact not found: {export_file}\n"
                f"Expected export file for language '{target_lang}' "
                f"in format '{ctx.answers.input_format}'\n"
                f"Run directory contents: {list(run_dir.glob('*'))}"
            )

            # Verify the export file is not empty
            content = export_file.read_text(encoding="utf-8")
            assert len(content.strip()) > 0, f"Export artifact is empty: {export_file}"


def test_env_var_scoping_regression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that monkeypatch env var setup is scoped to the test.

    This regression test ensures that the API key environment variable set
    during agent pool building doesn't leak outside the test context and that
    the BDD test doesn't rely on external shell environment.

    This addresses the audit feedback about deterministic test execution.
    Uses monkeypatch.context() to prove temporary override + restoration
    regardless of pre-existing environment state.
    """
    # Capture the original state (might be set or unset)
    original_value = os.environ.get("OPENROUTER_API_KEY")

    # Generate a project with default answers
    answers = InitAnswers(
        project_name="test-env-scope",
        game_name="Test Game",
        source_language="ja",
        target_languages=["en"],
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        model_id="openai/gpt-4-turbo",
        input_format=FileFormat.JSONL,
        include_seed_data=True,
    )

    target_dir = tmp_path / "test-env-scope"
    target_dir.mkdir()
    generate_project(answers, target_dir)

    # Load the generated config
    config_path = target_dir / "rentl.toml"
    with config_path.open("rb") as handle:
        payload: dict[str, JsonValue] = tomllib.load(handle)
    config = validate_run_config(payload)

    # Use isolated patch scope to verify temporary override + restoration
    with monkeypatch.context() as m:
        # Temporarily set the API key within the isolated scope
        m.setenv("OPENROUTER_API_KEY", "fake-api-key-for-scoping-test")

        # Verify it's set within the monkeypatch scope
        assert os.environ.get("OPENROUTER_API_KEY") == "fake-api-key-for-scoping-test"

        # Build agent pools (this should work with the monkeypatched env var)
        pools = build_agent_pools(config=config)
        assert pools is not None

    # After exiting the context, verify restoration to original state
    assert os.environ.get("OPENROUTER_API_KEY") == original_value


def test_all_provider_presets_produce_valid_configs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that all provider presets produce valid, runnable configs.

    This integration test ensures that:
    1. Each provider preset in PROVIDER_PRESETS is complete and valid
    2. The preset values can generate a valid rentl.toml
    3. The generated config passes schema validation
    4. Agent pools can be built from the generated config (proving API compatibility)

    This is a regression guard against incomplete or misconfigured presets.
    """
    for preset in PROVIDER_PRESETS:
        # Create answers using the preset
        answers = InitAnswers(
            project_name=f"test-{preset.provider_name}",
            game_name="Test Game",
            source_language="ja",
            target_languages=["en"],
            provider_name=preset.provider_name,
            base_url=preset.base_url,
            api_key_env=preset.api_key_env,
            model_id=preset.model_id,
            input_format=FileFormat.JSONL,
            include_seed_data=True,
        )

        # Generate project in preset-specific directory
        preset_dir = tmp_path / preset.provider_name
        preset_dir.mkdir()
        result = generate_project(answers, preset_dir)

        # Verify files were created
        assert len(result.created_files) > 0, f"No files created for {preset.name}"

        # Load and validate the generated config
        config_path = preset_dir / "rentl.toml"
        assert config_path.exists(), f"Config not created for {preset.name}"

        with config_path.open("rb") as handle:
            payload: dict[str, JsonValue] = tomllib.load(handle)

        config = validate_run_config(payload)
        assert config is not None, f"Config validation failed for {preset.name}"

        # Verify endpoint matches preset
        assert config.endpoint is not None
        assert config.endpoint.provider_name == preset.provider_name, (
            f"Provider name mismatch for {preset.name}"
        )
        assert config.endpoint.base_url == preset.base_url, (
            f"Base URL mismatch for {preset.name}"
        )
        assert config.endpoint.api_key_env == preset.api_key_env, (
            f"API key env mismatch for {preset.name}"
        )

        # Verify default model matches preset
        assert config.pipeline.default_model is not None
        assert config.pipeline.default_model.model_id == preset.model_id, (
            f"Model ID mismatch for {preset.name}"
        )

        # Set the API key environment variable for agent pool building
        # (different presets use different env var names)
        monkeypatch.setenv(preset.api_key_env, "fake-api-key-for-testing")

        # Verify agent pools can be built
        # This proves the config is compatible with the agent system
        pools = build_agent_pools(config=config)
        assert pools is not None, f"Agent pools failed to build for {preset.name}"
        assert len(pools.context_agents) > 0, f"No context agents for {preset.name}"
        assert len(pools.translate_agents) > 0, f"No translate agents for {preset.name}"
