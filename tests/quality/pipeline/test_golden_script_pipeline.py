"""BDD quality tests for full pipeline smoke test on golden script.

These tests verify that the full pipeline can run all phases on the golden
sample script using real LLM runtime (requires actual HTTP endpoint).
"""

from __future__ import annotations

import contextlib
import json
import shutil
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl_cli.main as cli_main
from rentl_schemas.io import TranslatedLine

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/pipeline/golden_script_pipeline.feature")


def _write_full_pipeline_config(
    config_path: Path, workspace_dir: Path, script_path: Path
) -> Path:
    """Write a rentl.toml config for full pipeline tests with all phases enabled.

    Returns:
        Path to the written config file.
    """
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
        base_url = "http://localhost:8001/v1"
        api_key_env = "PRIMARY_KEY"

        [pipeline.default_model]
        model_id = "gpt-4"
        endpoint_ref = "primary"

        [[pipeline.phases]]
        phase = "ingest"

        [[pipeline.phases]]
        phase = "context"
        agents = ["scene_summarizer"]

        [[pipeline.phases]]
        phase = "pretranslation"
        agents = ["idiom_labeler"]

        [[pipeline.phases]]
        phase = "translate"
        agents = ["direct_translator"]

        [[pipeline.phases]]
        phase = "qa"
        agents = ["style_guide_critic"]

        [[pipeline.phases]]
        phase = "edit"
        agents = ["basic_editor"]

        [[pipeline.phases]]
        phase = "export"

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


@given("the golden script exists at samples/golden/script.jsonl", target_fixture="ctx")
def given_golden_script_exists() -> PipelineContext:
    """Verify the golden script exists.

    Returns:
        PipelineContext with golden_script_path initialized.
    """
    ctx = PipelineContext()
    ctx.golden_script_path = Path("samples/golden/script.jsonl")
    assert ctx.golden_script_path.exists(), (
        f"Golden script not found at {ctx.golden_script_path}"
    )
    return ctx


@given("a pipeline config with all phases enabled")
def given_pipeline_config(
    ctx: PipelineContext,
    tmp_path: Path,
) -> None:
    """Create a config with all phases enabled."""
    assert ctx.golden_script_path is not None
    ctx.workspace_dir = tmp_path / "workspace"
    ctx.workspace_dir.mkdir()

    # Copy golden script to temp workspace for isolation
    script_copy = ctx.workspace_dir / "script.jsonl"
    shutil.copy(ctx.golden_script_path, script_copy)

    ctx.config_path = _write_full_pipeline_config(
        tmp_path, ctx.workspace_dir, script_copy
    )


@when("I run the full pipeline on the golden script")
def when_run_full_pipeline(ctx: PipelineContext, cli_runner: CliRunner) -> None:
    """Run the full pipeline CLI command."""
    assert ctx.config_path is not None
    ctx.result = cli_runner.invoke(
        cli_main.app,
        ["run-pipeline", "--config", str(ctx.config_path)],
    )
    if ctx.result.stdout:
        # If stdout is not valid JSON, leave response as None
        with contextlib.suppress(json.JSONDecodeError):
            ctx.response = json.loads(ctx.result.stdout)


@then("all phases complete successfully")
def then_all_phases_complete(ctx: PipelineContext) -> None:
    """Assert all phases complete successfully."""
    assert ctx.result is not None

    # If test failed, try to read logs for debugging
    if ctx.result.exit_code != 0 and ctx.workspace_dir:
        logs_dir = ctx.workspace_dir / "logs"
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.jsonl"))
            if log_files:
                log_content = log_files[0].read_text()
                # Only print first 5000 chars to avoid overwhelming output
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


@then("the export output contains valid TranslatedLine records")
def then_export_output_valid(ctx: PipelineContext) -> None:
    """Assert export output contains valid TranslatedLine records."""
    assert ctx.workspace_dir is not None
    assert ctx.response is not None

    # Find the export output file
    output_dir = ctx.workspace_dir / "out"
    assert output_dir.exists(), f"Output directory not found at {output_dir}"

    # Find the export file (should be a .jsonl file)
    export_files = list(output_dir.glob("*.jsonl"))
    assert len(export_files) > 0, f"No export output files found in {output_dir}"

    # Read and validate the export output
    export_file = export_files[0]
    translated_lines = []
    with open(export_file) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                # Validate as TranslatedLine
                translated_line = TranslatedLine.model_validate(data)
                translated_lines.append(translated_line)

    # Verify we got translated lines
    assert len(translated_lines) > 0, "Export output is empty"

    # Store for potential further assertions
    ctx.export_output = translated_lines

    # Verify all translated lines have required fields
    for tl in translated_lines:
        assert tl.line_id, f"TranslatedLine missing line_id: {tl}"
        assert tl.text, f"TranslatedLine missing text for {tl.line_id}"
