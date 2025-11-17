"""Helpers for loading and mutating project metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import anyio
import orjson

from rentl_core.io.loader import (
    load_character_metadata,
    load_game_metadata,
    load_glossary_entries,
    load_location_metadata,
    load_route_metadata,
    load_scene_file,
    load_scene_metadata,
)
from rentl_core.model.character import CharacterMetadata
from rentl_core.model.game import GameMetadata
from rentl_core.model.glossary import GlossaryEntry
from rentl_core.model.line import SourceLine
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneMetadata


@dataclass
class ProjectContext:
    """In-memory representation of a rentl project."""

    project_path: Path
    game: GameMetadata
    characters: dict[str, CharacterMetadata]
    glossary: list[GlossaryEntry]
    locations: dict[str, LocationMetadata]
    routes: dict[str, RouteMetadata]
    scenes: dict[str, SceneMetadata]
    metadata_dir: Path
    scenes_dir: Path
    context_docs_dir: Path

    def get_scene(self, scene_id: str) -> SceneMetadata:
        """Return metadata for *scene_id* or raise if missing.

        Raises:
            KeyError: If the scene id is unknown.

        Returns:
            SceneMetadata: Metadata for the requested scene.
        """
        if scene_id not in self.scenes:
            message = f"Unknown scene id: {scene_id}"
            raise KeyError(message)
        return self.scenes[scene_id]

    async def load_scene_lines(self, scene_id: str) -> list[SourceLine]:
        """Load the raw lines for *scene_id*.

        Raises:
            FileNotFoundError: If the scene JSONL file does not exist.

        Returns:
            list[SourceLine]: Parsed scene lines.
        """
        scene_path = self.scenes_dir / f"{scene_id}.jsonl"
        if not scene_path.exists():
            message = f"Scene file missing: {scene_path}"
            raise FileNotFoundError(message)
        return await load_scene_file(scene_path)

    async def list_context_docs(self) -> list[str]:
        """Return the names of available context documents."""
        docs: list[str] = []
        async for child in anyio.Path(self.context_docs_dir).iterdir():
            if await child.is_file():
                docs.append(child.name)
        return sorted(docs)

    async def read_context_doc(self, filename: str) -> str:
        """Read the contents of a context document.

        Raises:
            FileNotFoundError: If the file is missing.

        Returns:
            str: File contents.
        """
        path = anyio.Path(self.context_docs_dir / filename)
        if not await path.exists():
            message = f"Context doc not found: {filename}"
            raise FileNotFoundError(message)
        return await path.read_text()

    async def set_scene_summary(self, scene_id: str, summary: str, allow_overwrite: bool = False) -> None:
        """Update the stored summary for *scene_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite without permission.
        """
        scene = self.get_scene(scene_id)
        if scene.annotations.summary and not allow_overwrite:
            message = f"Scene '{scene_id}' already has a summary."
            raise ValueError(message)

        updated_annotations = scene.annotations.model_copy(update={"summary": summary})
        updated_scene = scene.model_copy(update={"annotations": updated_annotations})
        self.scenes[scene_id] = updated_scene
        await self._write_scenes()

    async def _write_scenes(self) -> None:
        """Persist the current scene metadata to disk."""
        path = self.metadata_dir / "scenes.jsonl"
        lines = [orjson.dumps(self.scenes[key].model_dump()).decode("utf-8") for key in sorted(self.scenes)]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")


async def load_project_context(project_path: Path) -> ProjectContext:
    """Load project metadata and return a :class:`ProjectContext`.

    Returns:
        ProjectContext: Fully populated context.
    """
    metadata_dir = project_path / "metadata"
    scenes_dir = project_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"

    game = await load_game_metadata(metadata_dir / "game.json")
    characters = await load_character_metadata(metadata_dir / "characters.jsonl")
    glossary = await load_glossary_entries(metadata_dir / "glossary.jsonl")
    locations = await load_location_metadata(metadata_dir / "locations.jsonl")
    routes = await load_route_metadata(metadata_dir / "routes.jsonl")
    scenes = await load_scene_metadata(metadata_dir / "scenes.jsonl")

    return ProjectContext(
        project_path=project_path,
        game=game,
        characters={entry.id: entry for entry in characters},
        glossary=glossary,
        locations={entry.id: entry for entry in locations},
        routes={route.id: route for route in routes},
        scenes={scene.id: scene for scene in scenes},
        metadata_dir=metadata_dir,
        scenes_dir=scenes_dir,
        context_docs_dir=context_docs_dir,
    )
