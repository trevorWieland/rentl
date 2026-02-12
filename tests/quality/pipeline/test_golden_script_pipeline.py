"""BDD quality tests for per-phase pipeline smoke tests on golden script.

These tests verify that individual pipeline phases work with real LLM runtime.
Each scenario enables only the minimum required phases, isolating failures.

IMPORTANT: These tests require a real LLM endpoint to be running.
Set RENTL_QUALITY_API_KEY and RENTL_QUALITY_BASE_URL environment variables
before running. The test raises ValueError if these are not configured.
"""

from __future__ import annotations

import contextlib
import json
import os
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main
from rentl_schemas.io import TranslatedLine

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/pipeline/golden_script_pipeline.feature")

# 30s per scenario — matches quality test timing standard
pytestmark = pytest.mark.timeout(30)

# Number of golden script lines to use (reduces API calls)
_GOLDEN_SUBSET_SIZE = 5


def _write_pipeline_config(
    config_path: Path,
    workspace_dir: Path,
    script_path: Path,
    phases: list[str],
) -> Path:
    """Write a rentl.toml config with only the specified phases enabled.

    Uses RENTL_QUALITY_BASE_URL, RENTL_QUALITY_API_KEY, and RENTL_QUALITY_MODEL
    from environment.

    Returns:
        Path to the written config file.

    Raises:
        ValueError: If required environment variables are not set.
    """
    base_url = os.getenv("RENTL_QUALITY_BASE_URL")
    if not base_url:
        raise ValueError("RENTL_QUALITY_BASE_URL must be set for quality tests")
    model_id = os.getenv("RENTL_QUALITY_MODEL")
    if not model_id:
        raise ValueError("RENTL_QUALITY_MODEL must be set for quality tests")

    # Build phase entries — only enabled phases are included
    phase_agents = {
        "context": '["scene_summarizer"]',
        "pretranslation": '["idiom_labeler"]',
        "translate": '["direct_translator"]',
        "qa": '["style_guide_critic"]',
        "edit": '["basic_editor"]',
    }

    phase_blocks = []
    for phase in phases:
        agents_line = ""
        if phase in phase_agents:
            agents_line = f"\nagents = {phase_agents[phase]}"
        phase_blocks.append(f'[[pipeline.phases]]\nphase = "{phase}"{agents_line}')

    phases_toml = "\n\n".join(phase_blocks)

    content = textwrap.dedent(
        f"""\
        [project]
        schema_version = {{ major = 0, minor = 1, patch = 0 }}
        project_name = "golden-pipeline-test"

        [project.paths]
        workspace_dir = "{workspace_dir}"
        input_path = "{script_path}"
        output_dir = "out"
        logs_dir = "logs"

        [project.formats]
        input_format = "jsonl"
        output_format = "jsonl"

        [project.languages]
        source_language = "ja"
        target_languages = ["en"]

        [logging]
        [[logging.sinks]]
        type = "file"

        [endpoints]
        default = "primary"

        [[endpoints.endpoints]]
        provider_name = "primary"
        base_url = "{base_url}"
        api_key_env = "RENTL_QUALITY_API_KEY"

        [pipeline.default_model]
        model_id = "{model_id}"
        endpoint_ref = "primary"

        {phases_toml}

        [concurrency]
        max_parallel_requests = 1
        max_parallel_scenes = 1

        [retry]
        max_retries = 1
        backoff_s = 1.0
        max_backoff_s = 2.0

        [cache]
        enabled = false
        """
    )
    file_path = config_path / "rentl.toml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


class PipelineContext:
    """Context object for pipeline BDD scenarios."""

    golden_script_path: Path | None = None
    config_path: Path | None = None
    workspace_dir: Path | None = None
    result: Result | None = None
    response: dict | None = None
    export_output: list[TranslatedLine] | None = None


def _setup_workspace(ctx: PipelineContext, tmp_path: Path, phases: list[str]) -> None:
    """Create workspace with golden script subset and pipeline config."""
    assert ctx.golden_script_path is not None
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()

    # Copy only first N lines of golden script for faster tests
    full_lines = ctx.golden_script_path.read_text(encoding="utf-8").splitlines()
    subset_lines = full_lines[:_GOLDEN_SUBSET_SIZE]
    script_copy = ctx.workspace_dir / "script.jsonl"
    script_copy.write_text("\n".join(subset_lines) + "\n", encoding="utf-8")

    ctx.config_path = _write_pipeline_config(
        tmp_path, ctx.workspace_dir, script_copy, phases
    )


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("a small subset of the golden script", target_fixture="ctx")
def given_golden_script_subset() -> PipelineContext:
    """Load a small subset of the golden script.

    Returns:
        PipelineContext with golden_script_path initialized.
    """
    ctx = PipelineContext()
    ctx.golden_script_path = Path("samples/golden/script.jsonl")
    assert ctx.golden_script_path.exists(), (
        f"Golden script not found at {ctx.golden_script_path}"
    )
    return ctx


@given("a pipeline config with context phase enabled")
def given_config_context(ctx: PipelineContext, tmp_path: Path) -> None:
    """Create config with ingest + context phases."""
    _setup_workspace(ctx, tmp_path, ["ingest", "context"])


@given("a pipeline config with translate and export phases enabled")
def given_config_translate_export(ctx: PipelineContext, tmp_path: Path) -> None:
    """Create config with ingest + translate + export phases."""
    _setup_workspace(ctx, tmp_path, ["ingest", "translate", "export"])


@given("a pipeline config with translate and qa phases enabled")
def given_config_translate_qa(ctx: PipelineContext, tmp_path: Path) -> None:
    """Create config with ingest + translate + qa phases."""
    _setup_workspace(ctx, tmp_path, ["ingest", "translate", "qa"])


@given("a pipeline config with translate and edit phases enabled")
def given_config_translate_edit(ctx: PipelineContext, tmp_path: Path) -> None:
    """Create config with ingest + translate + edit phases."""
    _setup_workspace(ctx, tmp_path, ["ingest", "translate", "edit"])


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when("I run the pipeline")
def when_run_pipeline(ctx: PipelineContext, cli_runner: CliRunner) -> None:
    """Run the pipeline CLI command."""
    assert ctx.config_path is not None
    ctx.result = cli_runner.invoke(
        cli_main.app,
        ["run-pipeline", "--config", str(ctx.config_path)],
    )
    if ctx.result.stdout:
        with contextlib.suppress(json.JSONDecodeError):
            ctx.response = json.loads(ctx.result.stdout)


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


def _assert_phase_ran(ctx: PipelineContext, phase_name: str) -> None:
    """Assert that a specific phase started and completed in the logs."""
    assert ctx.result is not None

    if ctx.result.exit_code != 0 and ctx.workspace_dir:
        logs_dir = ctx.workspace_dir / "logs"
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.jsonl"))
            if log_files:
                log_content = log_files[0].read_text()
                print(f"\nLog file content (first 5000 chars):\n{log_content[:5000]}")

    assert ctx.result.exit_code == 0, (
        f"Pipeline failed with exit code {ctx.result.exit_code}.\n"
        f"stdout: {ctx.result.stdout}\n"
        f"stderr: {ctx.result.stderr}"
    )

    assert ctx.workspace_dir is not None
    logs_dir = ctx.workspace_dir / "logs"
    assert logs_dir.exists(), f"Logs directory not found at {logs_dir}"

    log_files = list(logs_dir.glob("*.jsonl"))
    assert len(log_files) > 0, f"No log files found in {logs_dir}"

    phase_started = set()
    phase_completed = set()
    log_file = log_files[0]
    with open(log_file) as f:
        for line in f:
            if line.strip():
                try:
                    event = json.loads(line)
                    event_type = event.get("event")
                    if event_type == "phase_started":
                        phase = event.get("data", {}).get("phase")
                        if phase:
                            phase_started.add(phase)
                    elif event_type == "phase_completed":
                        phase = event.get("data", {}).get("phase")
                        if phase:
                            phase_completed.add(phase)
                except json.JSONDecodeError:
                    continue

    assert phase_name in phase_started, (
        f"Phase {phase_name} did not start. Started phases: {phase_started}"
    )
    assert phase_name in phase_completed, (
        f"Phase {phase_name} did not complete. Completed phases: {phase_completed}"
    )


@then("the context phase completes successfully")
def then_context_phase_completes(ctx: PipelineContext) -> None:
    """Assert context phase ran successfully."""
    _assert_phase_ran(ctx, "context")


@then("the translate phase completes successfully")
def then_translate_phase_completes(ctx: PipelineContext) -> None:
    """Assert translate phase ran successfully."""
    _assert_phase_ran(ctx, "translate")


@then("the qa phase completes successfully")
def then_qa_phase_completes(ctx: PipelineContext) -> None:
    """Assert qa phase ran successfully."""
    _assert_phase_ran(ctx, "qa")


@then("the edit phase completes successfully")
def then_edit_phase_completes(ctx: PipelineContext) -> None:
    """Assert edit phase ran successfully."""
    _assert_phase_ran(ctx, "edit")


@then("the export output contains valid TranslatedLine records")
def then_export_output_valid(ctx: PipelineContext) -> None:
    """Assert export output contains valid TranslatedLine records."""
    assert ctx.workspace_dir is not None
    assert ctx.response is not None

    output_dir = ctx.workspace_dir / "out"
    assert output_dir.exists(), f"Output directory not found at {output_dir}"

    export_files = list(output_dir.glob("*.jsonl"))
    assert len(export_files) > 0, f"No export output files found in {output_dir}"

    export_file = export_files[0]
    translated_lines = []
    with open(export_file) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                translated_line = TranslatedLine.model_validate(data)
                translated_lines.append(translated_line)

    assert len(translated_lines) > 0, "Export output is empty"

    ctx.export_output = translated_lines

    for tl in translated_lines:
        assert tl.line_id, f"TranslatedLine missing line_id: {tl}"
        assert tl.text, f"TranslatedLine missing text for {tl.line_id}"
