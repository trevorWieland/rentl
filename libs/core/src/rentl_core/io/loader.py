"""Async loaders for rentl metadata and scene files."""

from __future__ import annotations

from pathlib import Path

import anyio
import orjson

from rentl_core.model.character import CharacterMetadata
from rentl_core.model.game import GameMetadata
from rentl_core.model.glossary import GlossaryEntry
from rentl_core.model.line import SourceLine
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneMetadata


async def _read_json(path: Path) -> dict:
    """Read a JSON file asynchronously and return the parsed payload.

    Returns:
        dict: Parsed JSON object.
    """
    data = await anyio.Path(path).read_bytes()
    return orjson.loads(data)


async def _read_jsonl(path: Path) -> list[dict]:
    """Read newline-delimited JSON records from *path*.

    Returns:
        list[dict]: Parsed records for each non-empty line.
    """
    records: list[dict] = []
    async with await anyio.open_file(path, "r", encoding="utf-8") as stream:
        async for raw_line in stream:
            line = raw_line.strip()
            if not line:
                continue
            records.append(orjson.loads(line))
    return records


async def load_game_metadata(path: Path) -> GameMetadata:
    """Load *game.json* into a :class:`GameMetadata` object.

    Returns:
        GameMetadata: Parsed metadata instance.
    """
    payload = await _read_json(path)
    return GameMetadata.model_validate(payload)


async def load_character_metadata(path: Path) -> list[CharacterMetadata]:
    """Load *characters.jsonl* entries.

    Returns:
        list[CharacterMetadata]: Parsed character entries.
    """
    entries = await _read_jsonl(path)
    return [CharacterMetadata.model_validate(entry) for entry in entries]


async def load_glossary_entries(path: Path) -> list[GlossaryEntry]:
    """Load *glossary.jsonl* entries.

    Returns:
        list[GlossaryEntry]: Parsed glossary entries.
    """
    entries = await _read_jsonl(path)
    return [GlossaryEntry.model_validate(entry) for entry in entries]


async def load_location_metadata(path: Path) -> list[LocationMetadata]:
    """Load *locations.jsonl* entries.

    Returns:
        list[LocationMetadata]: Parsed location entries.
    """
    entries = await _read_jsonl(path)
    return [LocationMetadata.model_validate(entry) for entry in entries]


async def load_route_metadata(path: Path) -> list[RouteMetadata]:
    """Load *routes.jsonl* entries.

    Returns:
        list[RouteMetadata]: Parsed route entries.
    """
    entries = await _read_jsonl(path)
    return [RouteMetadata.model_validate(entry) for entry in entries]


async def load_scene_metadata(path: Path) -> list[SceneMetadata]:
    """Load *scenes.jsonl* entries.

    Returns:
        list[SceneMetadata]: Parsed scene metadata entries.
    """
    entries = await _read_jsonl(path)
    return [SceneMetadata.model_validate(entry) for entry in entries]


async def load_scene_file(path: Path) -> list[SourceLine]:
    """Load a scene JSONL file into :class:`SourceLine` objects.

    Returns:
        list[SourceLine]: Parsed lines for the scene.
    """
    entries = await _read_jsonl(path)
    return [SourceLine.model_validate(entry) for entry in entries]


async def load_all_scene_files(scene_dir: Path) -> dict[str, list[SourceLine]]:
    """Load every ``*.jsonl`` file under *scene_dir*.

    Returns:
        dict[str, list[SourceLine]]: Mapping of scene id to parsed lines.
    """
    results: dict[str, list[SourceLine]] = {}

    async def _load(path: Path) -> None:
        lines = await load_scene_file(path)
        results[path.stem] = lines

    async with anyio.create_task_group() as tg:
        async for child in anyio.Path(scene_dir).iterdir():
            if child.suffix != ".jsonl":
                continue
            tg.start_soon(_load, Path(child))

    return {key: results[key] for key in sorted(results)}
