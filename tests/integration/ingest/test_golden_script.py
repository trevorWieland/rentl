"""BDD integration tests for golden script ingest.

These tests verify that the golden sample script can be ingested through
the JSONL adapter and produces correct SourceLine records.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from rentl_io.ingest import JsonlIngestAdapter
from rentl_schemas.io import IngestSource, SourceLine
from rentl_schemas.primitives import FileFormat

# Link feature file
scenarios("../features/ingest/golden_script.feature")


class IngestContext:
    """Context object for ingest BDD scenarios."""

    golden_script_path: Path | None = None
    ingested_lines: list[SourceLine] | None = None


@given("the golden script.jsonl file exists", target_fixture="ctx")
def given_golden_script_exists() -> IngestContext:
    """Verify the golden script exists.

    Returns:
        IngestContext with golden_script_path initialized.
    """
    ctx = IngestContext()
    # Path to golden script relative to project root
    ctx.golden_script_path = Path("samples/golden/script.jsonl")
    assert ctx.golden_script_path.exists(), (
        f"Golden script not found at {ctx.golden_script_path}"
    )
    return ctx


@when("I ingest the file through the JSONL adapter")
def when_ingest_through_jsonl_adapter(ctx: IngestContext) -> None:
    """Ingest the golden script through the JSONL adapter."""
    assert ctx.golden_script_path is not None

    source = IngestSource(
        input_path=str(ctx.golden_script_path),
        format=FileFormat.JSONL,
    )
    adapter = JsonlIngestAdapter()
    ctx.ingested_lines = asyncio.run(adapter.load_source(source))


@then("all lines are successfully parsed as SourceLine records")
def then_all_lines_parsed(ctx: IngestContext) -> None:
    """Assert all lines are successfully parsed."""
    assert ctx.ingested_lines is not None
    # Verify we got at least some lines
    assert len(ctx.ingested_lines) > 0, "No lines were ingested"
    # All should be SourceLine instances
    for line in ctx.ingested_lines:
        assert isinstance(line, SourceLine)


@then("line IDs match the expected values")
def then_line_ids_match(ctx: IngestContext) -> None:
    """Assert line IDs match expected pattern and golden data."""
    assert ctx.ingested_lines is not None
    assert ctx.golden_script_path is not None

    # Load expected line_ids from golden script
    expected_line_ids = []
    with open(ctx.golden_script_path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                expected_line_ids.append(data["line_id"])

    # Assert all line_ids match exactly
    actual_line_ids = [line.line_id for line in ctx.ingested_lines]
    assert actual_line_ids == expected_line_ids, (
        f"Line IDs do not match golden data.\n"
        f"Expected: {expected_line_ids}\n"
        f"Actual: {actual_line_ids}"
    )

    # Verify all line_ids follow the pattern: ^[a-z]+(?:_[0-9]+)+$
    pattern = re.compile(r"^[a-z]+(?:_[0-9]+)+$")
    for line in ctx.ingested_lines:
        assert pattern.match(line.line_id), (
            f"Line ID {line.line_id} does not match expected pattern"
        )


@then("text content matches the expected values")
def then_text_matches(ctx: IngestContext) -> None:
    """Assert text content matches expected values and golden data."""
    assert ctx.ingested_lines is not None
    assert ctx.golden_script_path is not None

    # Load expected text from golden script
    expected_texts = []
    with open(ctx.golden_script_path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                expected_texts.append(data["text"])

    # Assert all text matches exactly
    actual_texts = [line.text for line in ctx.ingested_lines]
    pairs = list(zip(actual_texts, expected_texts, strict=True))
    mismatch_idx = next(
        (i for i, (a, e) in enumerate(pairs) if a != e),
        len(actual_texts),
    )
    assert actual_texts == expected_texts, (
        f"Text content does not match golden data.\n"
        f"First mismatch at index {mismatch_idx}"
    )

    # Check that all lines have non-empty text
    for line in ctx.ingested_lines:
        assert line.text, f"Line {line.line_id} has empty text"


@then("speakers match the expected values")
def then_speakers_match(ctx: IngestContext) -> None:
    """Assert speakers match expected values and golden data."""
    assert ctx.ingested_lines is not None
    assert ctx.golden_script_path is not None

    # Load expected speakers from golden script
    expected_speakers = []
    with open(ctx.golden_script_path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                expected_speakers.append(data.get("speaker"))

    # Assert all speakers match exactly
    actual_speakers = [line.speaker for line in ctx.ingested_lines]
    pairs = list(zip(actual_speakers, expected_speakers, strict=True))
    mismatch_idx = next(
        (i for i, (a, e) in enumerate(pairs) if a != e),
        len(actual_speakers),
    )
    assert actual_speakers == expected_speakers, (
        f"Speakers do not match golden data.\nFirst mismatch at index {mismatch_idx}"
    )

    # Verify that there are multiple unique speakers
    speakers = {line.speaker for line in ctx.ingested_lines if line.speaker}
    assert len(speakers) >= 4, (
        f"Expected at least 4 unique speakers, found {len(speakers)}"
    )


@then("scene IDs match the expected values")
def then_scene_ids_match(ctx: IngestContext) -> None:
    """Assert scene IDs match expected values and golden data."""
    assert ctx.ingested_lines is not None
    assert ctx.golden_script_path is not None

    # Load expected scene_ids from golden script
    expected_scene_ids = []
    with open(ctx.golden_script_path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                expected_scene_ids.append(data.get("scene_id"))

    # Assert all scene_ids match exactly
    actual_scene_ids = [line.scene_id for line in ctx.ingested_lines]
    pairs = list(zip(actual_scene_ids, expected_scene_ids, strict=True))
    mismatch_idx = next(
        (i for i, (a, e) in enumerate(pairs) if a != e),
        len(actual_scene_ids),
    )
    assert actual_scene_ids == expected_scene_ids, (
        f"Scene IDs do not match golden data.\nFirst mismatch at index {mismatch_idx}"
    )

    # Verify there are multiple scenes
    scene_ids = {line.scene_id for line in ctx.ingested_lines if line.scene_id}
    assert len(scene_ids) >= 3, (
        f"Expected at least 3 unique scenes, found {len(scene_ids)}"
    )

    # Verify scene transitions occur
    scenes_in_order = [line.scene_id for line in ctx.ingested_lines if line.scene_id]
    unique_scenes = []
    for scene in scenes_in_order:
        if not unique_scenes or unique_scenes[-1] != scene:
            unique_scenes.append(scene)
    assert len(unique_scenes) >= 3, f"Expected scene transitions, found {unique_scenes}"
