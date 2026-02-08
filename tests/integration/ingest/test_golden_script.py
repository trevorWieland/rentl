"""BDD integration tests for golden script ingest.

These tests verify that the golden sample script can be ingested through
the JSONL adapter and produces correct SourceLine records.
"""

from __future__ import annotations

import asyncio
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
    # Golden script has 58 lines
    assert len(ctx.ingested_lines) == 58, (
        f"Expected 58 lines, got {len(ctx.ingested_lines)}"
    )
    # All should be SourceLine instances
    for line in ctx.ingested_lines:
        assert isinstance(line, SourceLine)


@then("line IDs match the expected values")
def then_line_ids_match(ctx: IngestContext) -> None:
    """Assert line IDs match expected pattern."""
    assert ctx.ingested_lines is not None

    # Check first few line IDs
    expected_first_ids = [
        "scene_001_0001",
        "scene_001_0002",
        "scene_001_0003",
        "scene_001_0004",
        "scene_001_0005",
    ]
    actual_first_ids = [line.line_id for line in ctx.ingested_lines[:5]]
    assert actual_first_ids == expected_first_ids, (
        f"First line IDs mismatch: {actual_first_ids}"
    )

    # Verify all line_ids follow the pattern: ^[a-z]+(?:_[0-9]+)+$
    pattern = re.compile(r"^[a-z]+(?:_[0-9]+)+$")
    for line in ctx.ingested_lines:
        assert pattern.match(line.line_id), (
            f"Line ID {line.line_id} does not match expected pattern"
        )


@then("text content matches the expected values")
def then_text_matches(ctx: IngestContext) -> None:
    """Assert text content matches expected values."""
    assert ctx.ingested_lines is not None

    # Check first line text
    first_line = ctx.ingested_lines[0]
    assert first_line.text == "春の朝、桜の花びらが風に舞う学園の門。", (
        f"First line text mismatch: {first_line.text}"
    )

    # Check that all lines have non-empty text
    for line in ctx.ingested_lines:
        assert line.text, f"Line {line.line_id} has empty text"


@then("speakers match the expected values")
def then_speakers_match(ctx: IngestContext) -> None:
    """Assert speakers match expected values."""
    assert ctx.ingested_lines is not None

    # Check second line has unknown speaker
    second_line = ctx.ingested_lines[1]
    assert second_line.speaker == "???", (
        f"Expected unknown speaker '???', got {second_line.speaker}"
    )

    # Check fourth line has a named speaker
    fourth_line = ctx.ingested_lines[3]
    assert fourth_line.speaker == "佐藤健太", (
        f"Expected speaker '佐藤健太', got {fourth_line.speaker}"
    )

    # Verify that there are multiple unique speakers
    speakers = {line.speaker for line in ctx.ingested_lines if line.speaker}
    assert len(speakers) >= 4, (
        f"Expected at least 4 unique speakers, found {len(speakers)}"
    )


@then("scene IDs match the expected values")
def then_scene_ids_match(ctx: IngestContext) -> None:
    """Assert scene IDs match expected values."""
    assert ctx.ingested_lines is not None

    # Verify there are multiple scenes
    scene_ids = {line.scene_id for line in ctx.ingested_lines if line.scene_id}
    assert len(scene_ids) >= 3, (
        f"Expected at least 3 unique scenes, found {len(scene_ids)}"
    )

    # Check first line is in scene_001
    first_line = ctx.ingested_lines[0]
    assert first_line.scene_id == "scene_001", (
        f"First line scene_id mismatch: {first_line.scene_id}"
    )

    # Verify scene transitions occur
    scenes_in_order = [line.scene_id for line in ctx.ingested_lines if line.scene_id]
    unique_scenes = []
    for scene in scenes_in_order:
        if not unique_scenes or unique_scenes[-1] != scene:
            unique_scenes.append(scene)
    assert len(unique_scenes) >= 3, f"Expected scene transitions, found {unique_scenes}"
