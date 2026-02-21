"""BDD integration tests for export CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import Result
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import rentl.main as cli_main

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.integration

# Link feature file
scenarios("../features/cli/export.feature")


class ExportContext:
    """Context object for export BDD scenarios."""

    input_path: Path | None = None
    output_path: Path | None = None
    result: Result | None = None
    response: dict | None = None


@given("a JSONL file with translated lines", target_fixture="ctx")
def given_jsonl_with_translated_lines(tmp_path: Path) -> ExportContext:
    """Create a JSONL file with translated lines.

    Returns:
        ExportContext with input and output paths set.
    """
    ctx = ExportContext()
    ctx.input_path = tmp_path / "translated.jsonl"
    ctx.output_path = tmp_path / "output"

    lines = [
        {
            "line_id": "line_001",
            "source_text": "こんにちは",
            "text": "Hello",
            "scene_id": "scene_01",
        },
        {
            "line_id": "line_002",
            "source_text": "さようなら",
            "text": "Goodbye",
            "scene_id": "scene_01",
        },
    ]
    content = "\n".join(json.dumps(line) for line in lines) + "\n"
    ctx.input_path.write_text(content, encoding="utf-8")
    return ctx


@given("a JSONL file with untranslated lines", target_fixture="ctx")
def given_jsonl_with_untranslated_lines(tmp_path: Path) -> ExportContext:
    """Create a JSONL file with untranslated lines.

    Returns:
        ExportContext with input and output paths set.
    """
    ctx = ExportContext()
    ctx.input_path = tmp_path / "untranslated.jsonl"
    ctx.output_path = tmp_path / "output"

    # Empty text is untranslated (text is required and min_length=1). We use a line
    # without text field - this triggers validation error.
    lines = [
        {
            "line_id": "line_001",
            "source_text": "こんにちは",
            "scene_id": "scene_01",
            # text field missing - this should fail validation
        },
    ]
    content = "\n".join(json.dumps(line) for line in lines) + "\n"
    ctx.input_path.write_text(content, encoding="utf-8")
    return ctx


@when("I export to CSV format")
def when_export_to_csv(ctx: ExportContext, cli_runner: CliRunner) -> None:
    """Run the export command with CSV format."""
    assert ctx.output_path is not None
    output = ctx.output_path.with_suffix(".csv")
    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "export",
            "--input",
            str(ctx.input_path),
            "--output",
            str(output),
            "--format",
            "csv",
        ],
    )
    ctx.output_path = output
    if ctx.result.stdout:
        ctx.response = json.loads(ctx.result.stdout)


@when("I export to TXT format")
def when_export_to_txt(ctx: ExportContext, cli_runner: CliRunner) -> None:
    """Run the export command with TXT format."""
    assert ctx.output_path is not None
    output = ctx.output_path.with_suffix(".txt")
    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "export",
            "--input",
            str(ctx.input_path),
            "--output",
            str(output),
            "--format",
            "txt",
        ],
    )
    ctx.output_path = output
    if ctx.result.stdout:
        ctx.response = json.loads(ctx.result.stdout)


@when("I export with default untranslated policy")
def when_export_with_default_policy(ctx: ExportContext, cli_runner: CliRunner) -> None:
    """Run the export command with default (error) untranslated policy."""
    assert ctx.output_path is not None
    output = ctx.output_path.with_suffix(".csv")
    ctx.result = cli_runner.invoke(
        cli_main.app,
        [
            "export",
            "--input",
            str(ctx.input_path),
            "--output",
            str(output),
            "--format",
            "csv",
        ],
    )
    ctx.output_path = output
    if ctx.result.stdout:
        ctx.response = json.loads(ctx.result.stdout)


@then("the output file contains all lines in CSV format")
def then_output_csv_contains_lines(ctx: ExportContext) -> None:
    """Assert the CSV output file contains all lines."""
    # Check that the command succeeded with no error
    assert ctx.response is not None
    assert ctx.response.get("error") is None, (
        f"Export failed: {ctx.response.get('error')}"
    )
    # Check the output file exists
    assert ctx.output_path is not None
    assert ctx.output_path.exists(), f"Output file not created: {ctx.output_path}"
    content = ctx.output_path.read_text(encoding="utf-8")
    assert "Hello" in content
    assert "Goodbye" in content


@then("the output file contains all lines in TXT format")
def then_output_txt_contains_lines(ctx: ExportContext) -> None:
    """Assert the TXT output file contains all lines."""
    # Check that the command succeeded with no error
    assert ctx.response is not None
    assert ctx.response.get("error") is None, (
        f"Export failed: {ctx.response.get('error')}"
    )
    # Check the output file exists
    assert ctx.output_path is not None
    assert ctx.output_path.exists(), f"Output file not created: {ctx.output_path}"
    content = ctx.output_path.read_text(encoding="utf-8")
    assert "Hello" in content
    assert "Goodbye" in content
