"""Unit tests for benchmark output loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from anyio import Path as AsyncPath

from rentl_core.benchmark.output_loader import (
    OutputLoadError,
    load_output,
    validate_matching_line_ids,
)
from rentl_schemas.io import TranslatedLine


@pytest.fixture
def valid_output_data() -> list[dict]:
    """Valid TranslatedLine data for testing.

    Returns:
        List of dictionaries representing TranslatedLine data
    """
    return [
        {
            "line_id": "scene_1_1",
            "route_id": "route_1",
            "scene_id": "scene_1",
            "speaker": "Alice",
            "source_text": "Hello",
            "text": "こんにちは",
            "metadata": None,
            "source_columns": None,
        },
        {
            "line_id": "scene_1_2",
            "route_id": "route_1",
            "scene_id": "scene_1",
            "speaker": "Bob",
            "source_text": "Goodbye",
            "text": "さようなら",
            "metadata": None,
            "source_columns": None,
        },
    ]


@pytest.fixture
def valid_output_file(tmp_path: Path, valid_output_data: list[dict]) -> Path:
    """Create a valid JSONL output file.

    Returns:
        Path to the created JSONL file
    """
    output_file = tmp_path / "output.jsonl"
    with output_file.open("w", encoding="utf-8") as f:
        for data in valid_output_data:
            f.write(json.dumps(data) + "\n")
    return output_file


@pytest.mark.asyncio
async def test_load_output_success(
    valid_output_file: Path, valid_output_data: list[dict]
) -> None:
    """Test loading a valid output file."""
    lines = await load_output(AsyncPath(valid_output_file))

    assert len(lines) == 2
    assert isinstance(lines[0], TranslatedLine)
    assert lines[0].line_id == "scene_1_1"
    assert lines[0].text == "こんにちは"
    assert lines[1].line_id == "scene_1_2"
    assert lines[1].text == "さようなら"


@pytest.mark.asyncio
async def test_load_output_file_not_found(tmp_path: Path) -> None:
    """Test loading a non-existent file."""
    missing_file = AsyncPath(tmp_path / "missing.jsonl")

    with pytest.raises(OutputLoadError, match="Output file not found"):
        await load_output(missing_file)


@pytest.mark.asyncio
async def test_load_output_path_is_directory(tmp_path: Path) -> None:
    """Test loading when path is a directory."""
    directory = tmp_path / "dir"
    directory.mkdir()

    with pytest.raises(OutputLoadError, match="Output path is not a file"):
        await load_output(AsyncPath(directory))


@pytest.mark.asyncio
async def test_load_output_empty_file(tmp_path: Path) -> None:
    """Test loading an empty file."""
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("")

    with pytest.raises(OutputLoadError, match="Output file is empty"):
        await load_output(AsyncPath(empty_file))


@pytest.mark.asyncio
async def test_load_output_blank_lines_only(tmp_path: Path) -> None:
    """Test loading a file with only blank lines."""
    blank_file = tmp_path / "blank.jsonl"
    blank_file.write_text("\n\n  \n\n")

    with pytest.raises(OutputLoadError, match="Output file is empty"):
        await load_output(AsyncPath(blank_file))


@pytest.mark.asyncio
async def test_load_output_invalid_json(tmp_path: Path) -> None:
    """Test loading a file with invalid JSON."""
    invalid_file = tmp_path / "invalid.jsonl"
    invalid_file.write_text('{"line_id": "test"\n')  # Missing closing brace

    with pytest.raises(OutputLoadError, match=r"Invalid JSON.*:1:"):
        await load_output(AsyncPath(invalid_file))


@pytest.mark.asyncio
async def test_load_output_invalid_schema(tmp_path: Path) -> None:
    """Test loading a file with data that doesn't match TranslatedLine schema."""
    invalid_file = tmp_path / "invalid.jsonl"
    # Missing required 'text' field
    invalid_file.write_text('{"line_id": "test"}\n')

    with pytest.raises(OutputLoadError, match=r"Invalid TranslatedLine.*:1:"):
        await load_output(AsyncPath(invalid_file))


@pytest.mark.asyncio
async def test_load_output_mixed_valid_invalid(
    tmp_path: Path, valid_output_data: list[dict]
) -> None:
    """Test loading a file with valid lines followed by invalid JSON."""
    mixed_file = tmp_path / "mixed.jsonl"
    with mixed_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(valid_output_data[0]) + "\n")
        f.write('{"invalid": "json\n')  # Invalid JSON on line 2

    with pytest.raises(OutputLoadError, match=r"Invalid JSON.*:2:"):
        await load_output(AsyncPath(mixed_file))


@pytest.mark.asyncio
async def test_load_output_skips_blank_lines(
    tmp_path: Path, valid_output_data: list[dict]
) -> None:
    """Test that blank lines are skipped without error."""
    output_file = tmp_path / "with_blanks.jsonl"
    with output_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(valid_output_data[0]) + "\n")
        f.write("\n")
        f.write("  \n")
        f.write(json.dumps(valid_output_data[1]) + "\n")

    lines = await load_output(AsyncPath(output_file))
    assert len(lines) == 2


def test_validate_matching_line_ids_success() -> None:
    """Test validation when all outputs have matching line IDs."""
    outputs = {
        "candidate_a": [
            TranslatedLine(line_id="scene_1_1", text="Translation A1"),
            TranslatedLine(line_id="scene_1_2", text="Translation A2"),
        ],
        "candidate_b": [
            TranslatedLine(line_id="scene_1_1", text="Translation B1"),
            TranslatedLine(line_id="scene_1_2", text="Translation B2"),
        ],
        "candidate_c": [
            TranslatedLine(line_id="scene_1_1", text="Translation C1"),
            TranslatedLine(line_id="scene_1_2", text="Translation C2"),
        ],
    }

    # Should not raise
    validate_matching_line_ids(outputs)


def test_validate_matching_line_ids_no_outputs() -> None:
    """Test validation with no outputs."""
    with pytest.raises(OutputLoadError, match="No outputs provided"):
        validate_matching_line_ids({})


def test_validate_matching_line_ids_single_output() -> None:
    """Test validation with only one output."""
    outputs = {
        "candidate_a": [
            TranslatedLine(line_id="scene_1_1", text="Translation A1"),
        ],
    }

    with pytest.raises(OutputLoadError, match="At least 2 outputs required"):
        validate_matching_line_ids(outputs)


def test_validate_matching_line_ids_duplicate_ids_in_candidate() -> None:
    """Test validation when a candidate has duplicate line IDs."""
    outputs = {
        "candidate_a": [
            TranslatedLine(line_id="scene_1_1", text="Translation A1"),
            TranslatedLine(line_id="scene_1_1", text="Translation A1 duplicate"),
        ],
        "candidate_b": [
            TranslatedLine(line_id="scene_1_1", text="Translation B1"),
        ],
    }

    with pytest.raises(OutputLoadError, match="duplicate line IDs"):
        validate_matching_line_ids(outputs)


def test_validate_matching_line_ids_missing_lines() -> None:
    """Test validation when a candidate is missing some line IDs."""
    outputs = {
        "candidate_a": [
            TranslatedLine(line_id="scene_1_1", text="Translation A1"),
            TranslatedLine(line_id="scene_1_2", text="Translation A2"),
            TranslatedLine(line_id="scene_1_3", text="Translation A3"),
        ],
        "candidate_b": [
            TranslatedLine(line_id="scene_1_1", text="Translation B1"),
            # Missing scene_1_2
            TranslatedLine(line_id="scene_1_3", text="Translation B3"),
        ],
    }

    with pytest.raises(OutputLoadError, match="Line ID mismatch") as exc_info:
        validate_matching_line_ids(outputs)

    error_msg = str(exc_info.value)
    assert "candidate_a" in error_msg
    assert "candidate_b" in error_msg
    assert "Missing from" in error_msg or "Extra in" in error_msg


def test_validate_matching_line_ids_extra_lines() -> None:
    """Test validation when a candidate has extra line IDs."""
    outputs = {
        "candidate_a": [
            TranslatedLine(line_id="scene_1_1", text="Translation A1"),
            TranslatedLine(line_id="scene_1_2", text="Translation A2"),
        ],
        "candidate_b": [
            TranslatedLine(line_id="scene_1_1", text="Translation B1"),
            TranslatedLine(line_id="scene_1_2", text="Translation B2"),
            TranslatedLine(line_id="scene_1_3", text="Translation B3"),  # Extra
        ],
    }

    with pytest.raises(OutputLoadError, match="Line ID mismatch") as exc_info:
        validate_matching_line_ids(outputs)

    error_msg = str(exc_info.value)
    assert "candidate_a" in error_msg
    assert "candidate_b" in error_msg
    assert "Missing from" in error_msg or "Extra in" in error_msg


def test_validate_matching_line_ids_completely_different() -> None:
    """Test validation when candidates have completely different line IDs."""
    outputs = {
        "candidate_a": [
            TranslatedLine(line_id="scene_1_1", text="Translation A1"),
            TranslatedLine(line_id="scene_1_2", text="Translation A2"),
        ],
        "candidate_b": [
            TranslatedLine(line_id="scene_2_1", text="Translation B1"),
            TranslatedLine(line_id="scene_2_2", text="Translation B2"),
        ],
    }

    with pytest.raises(OutputLoadError, match="Line ID mismatch"):
        validate_matching_line_ids(outputs)


def test_validate_matching_line_ids_many_missing_truncated() -> None:
    """Test that error messages are truncated when many lines are missing."""
    # Create candidate_a with 100 lines
    candidate_a = [
        TranslatedLine(line_id=f"scene_{i}", text=f"Translation A{i}")
        for i in range(100)
    ]

    # Create candidate_b with only first 50 lines
    candidate_b = [
        TranslatedLine(line_id=f"scene_{i}", text=f"Translation B{i}")
        for i in range(50)
    ]

    outputs = {"candidate_a": candidate_a, "candidate_b": candidate_b}

    with pytest.raises(OutputLoadError, match="Line ID mismatch") as exc_info:
        validate_matching_line_ids(outputs)

    error_msg = str(exc_info.value)
    # Should truncate the list
    assert "and 45 more" in error_msg or "... and 45 more" in error_msg


def test_validate_matching_line_ids_order_independent() -> None:
    """Test that line order doesn't matter, only the set of IDs."""
    outputs = {
        "candidate_a": [
            TranslatedLine(line_id="scene_1_2", text="Translation A2"),
            TranslatedLine(line_id="scene_1_1", text="Translation A1"),
        ],
        "candidate_b": [
            TranslatedLine(line_id="scene_1_1", text="Translation B1"),
            TranslatedLine(line_id="scene_1_2", text="Translation B2"),
        ],
    }

    # Should not raise - order doesn't matter
    validate_matching_line_ids(outputs)


def test_validate_matching_line_ids_many_extra_truncated() -> None:
    """Test that error messages are truncated when many extra lines are present."""
    # Create candidate_a with 50 lines
    candidate_a = [
        TranslatedLine(line_id=f"scene_{i}", text=f"Translation A{i}")
        for i in range(50)
    ]

    # Create candidate_b with 100 lines (50 extra)
    candidate_b = [
        TranslatedLine(line_id=f"scene_{i}", text=f"Translation B{i}")
        for i in range(100)
    ]

    outputs = {"candidate_a": candidate_a, "candidate_b": candidate_b}

    with pytest.raises(OutputLoadError, match="Line ID mismatch") as exc_info:
        validate_matching_line_ids(outputs)

    error_msg = str(exc_info.value)
    # Should truncate the extra list
    assert "and 45 more" in error_msg or "... and 45 more" in error_msg
