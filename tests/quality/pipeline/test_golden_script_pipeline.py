"""BDD quality tests for per-phase pipeline verification on golden script.

These tests verify that each pipeline phase works correctly with real LLM
runtime by running isolated phase combinations on a small subset of the
golden sample script.

IMPORTANT: These tests require a real LLM endpoint to be running.
Set RENTL_QUALITY_API_KEY, RENTL_QUALITY_BASE_URL, and RENTL_QUALITY_MODEL
environment variables before running.
"""

from __future__ import annotations

import contextlib
import json
import os
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import Result
from dotenv import load_dotenv
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main
from rentl_schemas.config import RunConfig
from rentl_schemas.io import TranslatedLine

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/pipeline/golden_script_pipeline.feature")

# 30s timeout per scenario — standard enforces quality tests < 30s
pytestmark = pytest.mark.timeout(30)

# Single line from golden script — minimal input to validate pipeline
# integration path. Translation quality is covered by agent quality tests.
_GOLDEN_SUBSET_SIZE = 1


def _write_pipeline_config(
    config_path: Path,
    workspace_dir: Path,
    script_path: Path,
    phases: list[str],
) -> Path:
    """Write a rentl.toml config with only specified phases enabled.

    Args:
        config_path: Directory to write config into.
        workspace_dir: Pipeline workspace directory.
        script_path: Path to input script file.
        phases: List of phase names to enable.

    Returns:
        Path to the written config file.

    Raises:
        ValueError: If required environment variables are not set.
    """
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)

    base_url = os.getenv("RENTL_QUALITY_BASE_URL")
    if not base_url:
        raise ValueError("RENTL_QUALITY_BASE_URL must be set for quality tests")
    model_id = os.getenv("RENTL_QUALITY_MODEL")
    if not model_id:
        raise ValueError("RENTL_QUALITY_MODEL must be set for quality tests")

    # Phase definitions with their agent assignments
    phase_agents = {
        "context": "scene_summarizer",
        "pretranslation": "idiom_labeler",
        "translate": "direct_translator",
        "qa": "style_guide_critic",
        "edit": "basic_editor",
    }
    all_phases = [
        "ingest",
        "context",
        "pretranslation",
        "translate",
        "qa",
        "edit",
        "export",
    ]

    # Always include ingest as it's required by all other phases
    enabled_phases = {"ingest"} | set(phases)

    # Build phase blocks
    phase_lines: list[str] = []
    for phase_name in all_phases:
        enabled_str = str(phase_name in enabled_phases).lower()
        phase_lines.extend([
            "[[pipeline.phases]]",
            f'phase = "{phase_name}"',
            f"enabled = {enabled_str}",
        ])
        if phase_name in phase_agents:
            phase_lines.append(f'agents = ["{phase_agents[phase_name]}"]')
        phase_lines.append("")  # blank line separator

    phases_toml = "\n".join(phase_lines)

    # Build config without textwrap.dedent to avoid indent
    # corruption from multi-line variable interpolation
    content = (
        "[project]\n"
        "schema_version = { major = 0, minor = 1, patch = 0 }\n"
        'project_name = "golden-pipeline-test"\n'
        "\n"
        "[project.paths]\n"
        f'workspace_dir = "{workspace_dir}"\n'
        f'input_path = "{script_path}"\n'
        'output_dir = "out"\n'
        'logs_dir = "logs"\n'
        "\n"
        "[project.formats]\n"
        'input_format = "jsonl"\n'
        'output_format = "jsonl"\n'
        "\n"
        "[project.languages]\n"
        'source_language = "ja"\n'
        'target_languages = ["en"]\n'
        "\n"
        "[logging]\n"
        "[[logging.sinks]]\n"
        'type = "file"\n'
        "\n"
        "[endpoints]\n"
        'default = "primary"\n'
        "\n"
        "[[endpoints.endpoints]]\n"
        'provider_name = "primary"\n'
        f'base_url = "{base_url}"\n'
        'api_key_env = "RENTL_QUALITY_API_KEY"\n'
        "timeout_s = 10\n"
        "\n"
        "[pipeline.default_model]\n"
        f'model_id = "{model_id}"\n'
        'endpoint_ref = "primary"\n'
        "\n"
        f"{phases_toml}\n"
        "[concurrency]\n"
        "max_parallel_requests = 1\n"
        "max_parallel_scenes = 1\n"
        "\n"
        "[retry]\n"
        "max_retries = 0\n"
        "backoff_s = 1.0\n"
        "max_backoff_s = 2.0\n"
        "\n"
        "[cache]\n"
        "enabled = false\n"
    )
    file_path = config_path / "rentl.toml"
    file_path.write_text(content, encoding="utf-8")

    # Round-trip schema validation: ensure written config is a valid RunConfig
    with file_path.open("rb") as f:
        RunConfig.model_validate(tomllib.load(f))

    return file_path


class PipelineContext:
    """Context object for pipeline BDD scenarios."""

    golden_script_path: Path | None = None
    config_path: Path | None = None
    workspace_dir: Path | None = None
    result: Result | None = None
    response: dict | None = None
    export_output: list[TranslatedLine] | None = None


def _parse_log_phases(workspace_dir: Path) -> tuple[set[str], set[str]]:
    """Parse pipeline log file and return started/completed phase sets.

    Log events use the format ``{phase}_{suffix}`` (e.g. ``context_started``,
    ``translate_completed``), not ``phase_started``/``phase_completed``.

    Returns:
        Tuple of (phase_started, phase_completed) sets.
    """
    logs_dir = workspace_dir / "logs"
    assert logs_dir.exists(), f"Logs directory not found at {logs_dir}"

    log_files = list(logs_dir.glob("*.jsonl"))
    assert len(log_files) > 0, f"No log files found in {logs_dir}"

    phase_started: set[str] = set()
    phase_completed: set[str] = set()
    log_file = log_files[0]
    with open(log_file) as f:
        for line in f:
            if line.strip():
                try:
                    event = json.loads(line)
                    event_name = event.get("event", "")
                    if event_name.endswith("_started"):
                        phase = event_name.removesuffix("_started")
                        if phase != "run":
                            phase_started.add(phase)
                    elif event_name.endswith("_completed"):
                        phase = event_name.removesuffix("_completed")
                        if phase != "run":
                            phase_completed.add(phase)
                except json.JSONDecodeError:
                    continue

    return phase_started, phase_completed


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("a small subset of the golden script", target_fixture="ctx")
def given_small_golden_subset() -> PipelineContext:
    """Load only the first few lines of the golden script for speed.

    Returns:
        PipelineContext with golden_script_path initialized.
    """
    ctx = PipelineContext()
    full_script = Path("samples/golden/script.jsonl")
    assert full_script.exists(), f"Golden script not found at {full_script}"
    ctx.golden_script_path = full_script
    return ctx


@given(
    parsers.parse("a pipeline config with {phase_desc} enabled"),
    target_fixture="ctx",
    stacklevel=1,
)
def given_pipeline_config_phases(
    ctx: PipelineContext,
    tmp_path: Path,
    phase_desc: str,
) -> PipelineContext:
    """Create a pipeline config with specified phases enabled.

    Args:
        ctx: Pipeline context from previous given step.
        tmp_path: Pytest temporary directory.
        phase_desc: Description of phases, e.g. "context phase" or
            "translate and export phases".

    Returns:
        Updated PipelineContext with config and workspace.
    """
    assert ctx.golden_script_path is not None
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()

    # Copy subset of golden script to temp workspace
    script_copy = ctx.workspace_dir / "script.jsonl"
    with open(ctx.golden_script_path) as src, open(script_copy, "w") as dst:
        for i, line in enumerate(src):
            if i >= _GOLDEN_SUBSET_SIZE:
                break
            dst.write(line)

    # Parse phase names from description
    # "context phase" -> ["context"]
    # "translate and export phases" -> ["translate", "export"]
    # "translate and qa phases" -> ["translate", "qa"]
    phase_words = phase_desc.replace(" phases", "").replace(" phase", "")
    phases = [p.strip() for p in phase_words.split(" and ")]

    ctx.config_path = _write_pipeline_config(
        tmp_path, ctx.workspace_dir, script_copy, phases
    )
    return ctx


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


@then("the pipeline completes successfully")
def then_pipeline_completes(ctx: PipelineContext) -> None:
    """Assert the pipeline exits successfully with valid response."""
    assert ctx.result is not None

    # Print logs on failure for debugging
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
    assert ctx.response is not None, (
        f"No JSON response received.\nstdout: {ctx.result.stdout}"
    )
    assert ctx.response.get("error") is None, (
        f"Pipeline returned error: {ctx.response.get('error')}"
    )
    assert ctx.response.get("data") is not None
    assert ctx.response["data"].get("run_id") is not None


@then(parsers.parse("the {phase_name} phase completed in logs"))
def then_phase_completed_in_logs(ctx: PipelineContext, phase_name: str) -> None:
    """Assert a specific phase started and completed in pipeline logs."""
    assert ctx.workspace_dir is not None
    phase_started, phase_completed = _parse_log_phases(ctx.workspace_dir)

    assert phase_name in phase_started, (
        f"Phase {phase_name} did not start. Started phases: {phase_started}"
    )
    assert phase_name in phase_completed, (
        f"Phase {phase_name} did not complete. Completed phases: {phase_completed}"
    )


@then("the export output contains valid TranslatedLine records")
def then_export_output_valid(ctx: PipelineContext) -> None:
    """Assert export output contains valid TranslatedLine records."""
    assert ctx.workspace_dir is not None
    assert ctx.response is not None

    output_dir = ctx.workspace_dir / "out"
    assert output_dir.exists(), f"Output directory not found at {output_dir}"

    # Export writes to out/run-{uuid}/{lang}.jsonl
    export_files = list(output_dir.glob("**/*.jsonl"))
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
