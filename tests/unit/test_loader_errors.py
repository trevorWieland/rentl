"""Loader error cases to ensure failures surface clearly."""

from __future__ import annotations

from pathlib import Path

import orjson
import pytest
from rentl_core.io.loader import load_scene_metadata


@pytest.mark.anyio
async def test_load_scene_metadata_missing_file(tmp_path: Path) -> None:
    """Missing scene metadata should raise FileNotFoundError."""
    missing = tmp_path / "missing.jsonl"
    with pytest.raises(FileNotFoundError):
        await load_scene_metadata(missing)


@pytest.mark.anyio
async def test_load_scene_metadata_ignores_empty_lines(tmp_path: Path) -> None:
    """Blank lines should be ignored when reading JSONL."""
    scene_file = tmp_path / "scenes.jsonl"
    payload = {
        "id": "scene_1",
        "title": "Test",
        "title_origin": "human",
        "route_ids": [],
        "annotations": {
            "summary": None,
            "summary_origin": None,
            "tags": [],
            "tags_origin": None,
            "primary_characters": [],
            "primary_characters_origin": None,
            "locations": [],
            "locations_origin": None,
        },
    }
    scene_file.write_text(orjson.dumps(payload).decode("utf-8") + "\n\n")

    scenes = await load_scene_metadata(scene_file)
    assert len(scenes) == 1
    assert scenes[0].id == "scene_1"


@pytest.mark.anyio
async def test_load_scene_metadata_invalid_json_raises(tmp_path: Path) -> None:
    """Invalid JSON should surface as a JSON decode error."""
    scene_file = tmp_path / "scenes.jsonl"
    scene_file.write_text('{"id": "scene_1", "title": "Test" this is bad json}\n')

    with pytest.raises(orjson.JSONDecodeError):
        await load_scene_metadata(scene_file)
