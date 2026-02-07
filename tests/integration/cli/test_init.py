"""BDD integration tests for init CLI command."""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, scenarios, then, when

from rentl_agents.wiring import build_agent_pools
from rentl_core.init import InitAnswers, generate_project
from rentl_schemas.io import SourceLine
from rentl_schemas.primitives import FileFormat, JsonValue
from rentl_schemas.validation import validate_run_config

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
        model_id="openai/gpt-4.1",
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

    # Check that all expected files exist
    expected_files = [
        ctx.target_dir / "rentl.toml",
        ctx.target_dir / ".env",
        ctx.target_dir / "input",
        ctx.target_dir / "out",
        ctx.target_dir / "logs",
        ctx.target_dir / "input" / "seed.jsonl",
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

    seed_path = ctx.target_dir / "input" / f"seed.{ctx.answers.input_format}"
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


@then("the pipeline can build agent pools from generated config")
def then_pipeline_can_build_agent_pools(
    ctx: InitContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Assert the generated config can be used to build agent pools.

    This verifies that referenced agent names actually exist in the default pool,
    catching configuration errors that would only appear at runtime.

    Raises:
        AssertionError: If agent pool building fails.
    """
    assert ctx.config_path is not None
    assert ctx.answers is not None

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

    # Attempt to build agent pools - this will fail if agent names are invalid
    try:
        pools = build_agent_pools(config=config)
        assert pools is not None
        # Verify we got pools for the expected phases
        # Each phase should have at least one agent pool
        assert len(pools.context_agents) > 0
        assert len(pools.pretranslation_agents) > 0
        assert len(pools.translate_agents) > 0
        assert len(pools.qa_agents) > 0
        assert len(pools.edit_agents) > 0
    except Exception as exc:
        raise AssertionError(
            f"Failed to build agent pools from generated config: {exc}"
        ) from exc


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
        model_id="openai/gpt-4.1",
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
