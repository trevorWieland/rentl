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

    def get_character(self, character_id: str) -> CharacterMetadata:
        """Return metadata for *character_id* or raise if missing.

        Raises:
            KeyError: If the character id is unknown.

        Returns:
            CharacterMetadata: Metadata for the requested character.
        """
        if character_id not in self.characters:
            message = f"Unknown character id: {character_id}"
            raise KeyError(message)
        return self.characters[character_id]

    def get_location(self, location_id: str) -> LocationMetadata:
        """Return metadata for *location_id* or raise if missing.

        Raises:
            KeyError: If the location id is unknown.

        Returns:
            LocationMetadata: Metadata for the requested location.
        """
        if location_id not in self.locations:
            message = f"Unknown location id: {location_id}"
            raise KeyError(message)
        return self.locations[location_id]

    def get_route(self, route_id: str) -> RouteMetadata:
        """Return metadata for *route_id* or raise if missing.

        Raises:
            KeyError: If the route id is unknown.

        Returns:
            RouteMetadata: Metadata for the requested route.
        """
        if route_id not in self.routes:
            message = f"Unknown route id: {route_id}"
            raise KeyError(message)
        return self.routes[route_id]

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

    async def set_scene_summary(self, scene_id: str, summary: str, *, allow_overwrite: bool = False) -> None:
        """Update the stored summary for *scene_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite without permission.
        """
        from datetime import date

        scene = self.get_scene(scene_id)
        if scene.annotations.summary and not allow_overwrite:
            message = f"Scene '{scene_id}' already has a summary."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_annotations = scene.annotations.model_copy(
            update={"summary": summary, "summary_origin": f"agent:scene_detailer:{today}"}
        )
        updated_scene = scene.model_copy(update={"annotations": updated_annotations})
        self.scenes[scene_id] = updated_scene
        await self._write_scenes()

    async def set_scene_tags(self, scene_id: str, tags: list[str], *, allow_overwrite: bool = False) -> None:
        """Update the stored tags for *scene_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite without permission.
        """
        from datetime import date

        scene = self.get_scene(scene_id)
        if scene.annotations.tags and not allow_overwrite:
            message = f"Scene '{scene_id}' already has tags."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_annotations = scene.annotations.model_copy(
            update={"tags": tags, "tags_origin": f"agent:scene_detailer:{today}"}
        )
        updated_scene = scene.model_copy(update={"annotations": updated_annotations})
        self.scenes[scene_id] = updated_scene
        await self._write_scenes()

    async def set_scene_characters(
        self, scene_id: str, character_ids: list[str], *, allow_overwrite: bool = False
    ) -> None:
        """Update the stored primary characters for *scene_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite without permission.
        """
        from datetime import date

        scene = self.get_scene(scene_id)
        if scene.annotations.primary_characters and not allow_overwrite:
            message = f"Scene '{scene_id}' already has primary characters."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_annotations = scene.annotations.model_copy(
            update={"primary_characters": character_ids, "primary_characters_origin": f"agent:scene_detailer:{today}"}
        )
        updated_scene = scene.model_copy(update={"annotations": updated_annotations})
        self.scenes[scene_id] = updated_scene
        await self._write_scenes()

    async def set_scene_locations(
        self, scene_id: str, location_ids: list[str], *, allow_overwrite: bool = False
    ) -> None:
        """Update the stored locations for *scene_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite without permission.
        """
        from datetime import date

        scene = self.get_scene(scene_id)
        if scene.annotations.locations and not allow_overwrite:
            message = f"Scene '{scene_id}' already has locations."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_annotations = scene.annotations.model_copy(
            update={"locations": location_ids, "locations_origin": f"agent:scene_detailer:{today}"}
        )
        updated_scene = scene.model_copy(update={"annotations": updated_annotations})
        self.scenes[scene_id] = updated_scene
        await self._write_scenes()

    async def _write_scenes(self) -> None:
        """Persist the current scene metadata to disk."""
        path = self.metadata_dir / "scenes.jsonl"
        lines = [orjson.dumps(self.scenes[key].model_dump()).decode("utf-8") for key in sorted(self.scenes)]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def update_character_name_tgt(
        self, character_id: str, name_tgt: str, *, allow_overwrite: bool = False
    ) -> None:
        """Update the target language name for *character_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite human-authored data without permission.
        """
        from datetime import date

        character = self.get_character(character_id)
        if character.name_tgt and character.name_tgt_origin == "human" and not allow_overwrite:
            message = f"Character '{character_id}' has a human-authored target name."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_character = character.model_copy(
            update={"name_tgt": name_tgt, "name_tgt_origin": f"agent:character_detailer:{today}"}
        )
        self.characters[character_id] = updated_character
        await self._write_characters()

    async def update_character_pronouns(
        self, character_id: str, pronouns: str, *, allow_overwrite: bool = False
    ) -> None:
        """Update pronoun preferences for *character_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite human-authored data without permission.
        """
        from datetime import date

        character = self.get_character(character_id)
        if character.pronouns and character.pronouns_origin == "human" and not allow_overwrite:
            message = f"Character '{character_id}' has human-authored pronouns."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_character = character.model_copy(
            update={"pronouns": pronouns, "pronouns_origin": f"agent:character_detailer:{today}"}
        )
        self.characters[character_id] = updated_character
        await self._write_characters()

    async def update_character_notes(self, character_id: str, notes: str, *, allow_overwrite: bool = False) -> None:
        """Update character notes for *character_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite human-authored data without permission.
        """
        from datetime import date

        character = self.get_character(character_id)
        if character.notes and character.notes_origin == "human" and not allow_overwrite:
            message = f"Character '{character_id}' has human-authored notes."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_character = character.model_copy(
            update={"notes": notes, "notes_origin": f"agent:character_detailer:{today}"}
        )
        self.characters[character_id] = updated_character
        await self._write_characters()

    async def _write_characters(self) -> None:
        """Persist the current character metadata to disk."""
        path = self.metadata_dir / "characters.jsonl"
        lines = [orjson.dumps(self.characters[key].model_dump()).decode("utf-8") for key in sorted(self.characters)]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def update_location_name_tgt(self, location_id: str, name_tgt: str, *, allow_overwrite: bool = False) -> None:
        """Update the target language name for *location_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite human-authored data without permission.
        """
        from datetime import date

        location = self.get_location(location_id)
        if location.name_tgt and location.name_tgt_origin == "human" and not allow_overwrite:
            message = f"Location '{location_id}' has a human-authored target name."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_location = location.model_copy(
            update={"name_tgt": name_tgt, "name_tgt_origin": f"agent:location_detailer:{today}"}
        )
        self.locations[location_id] = updated_location
        await self._write_locations()

    async def update_location_description(
        self, location_id: str, description: str, *, allow_overwrite: bool = False
    ) -> None:
        """Update the description for *location_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite human-authored data without permission.
        """
        from datetime import date

        location = self.get_location(location_id)
        if location.description and location.description_origin == "human" and not allow_overwrite:
            message = f"Location '{location_id}' has a human-authored description."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_location = location.model_copy(
            update={"description": description, "description_origin": f"agent:location_detailer:{today}"}
        )
        self.locations[location_id] = updated_location
        await self._write_locations()

    async def _write_locations(self) -> None:
        """Persist the current location metadata to disk."""
        path = self.metadata_dir / "locations.jsonl"
        lines = [orjson.dumps(self.locations[key].model_dump()).decode("utf-8") for key in sorted(self.locations)]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def add_glossary_entry(
        self,
        term_src: str,
        term_tgt: str,
        notes: str | None = None,
        *,
        allow_overwrite: bool = False,
    ) -> None:
        """Add a new glossary entry and persist to disk.

        Raises:
            ValueError: If entry already exists.
        """
        from datetime import date

        # Check if entry already exists
        for entry in self.glossary:
            if entry.term_src == term_src:
                message = f"Glossary entry for '{term_src}' already exists."
                raise ValueError(message)

        today = date.today().isoformat()
        new_entry = GlossaryEntry(
            term_src=term_src,
            term_src_origin=f"agent:glossary_curator:{today}",
            term_tgt=term_tgt,
            term_tgt_origin=f"agent:glossary_curator:{today}",
            notes=notes,
            notes_origin=f"agent:glossary_curator:{today}" if notes else None,
        )
        self.glossary.append(new_entry)
        await self._write_glossary()

    async def update_glossary_entry(
        self,
        term_src: str,
        term_tgt: str | None = None,
        notes: str | None = None,
        *,
        allow_overwrite: bool = False,
    ) -> None:
        """Update an existing glossary entry and persist to disk.

        Args:
            term_src: Source term to update.
            term_tgt: New target term (optional, keeps existing if None).
            notes: New notes (optional, keeps existing if None).
            allow_overwrite: Allow overwriting human-authored data.

        Raises:
            ValueError: If entry not found or attempting to overwrite human data without permission.
        """
        from datetime import date

        # Find the entry
        entry_index = None
        for i, entry in enumerate(self.glossary):
            if entry.term_src == term_src:
                entry_index = i
                break

        if entry_index is None:
            message = f"Glossary entry for '{term_src}' not found."
            raise ValueError(message)

        entry = self.glossary[entry_index]
        today = date.today().isoformat()
        updates = {}

        # Check and update term_tgt
        if term_tgt is not None:
            if entry.term_tgt and entry.term_tgt_origin == "human" and not allow_overwrite:
                message = f"Glossary entry '{term_src}' has human-authored target term."
                raise ValueError(message)
            updates["term_tgt"] = term_tgt
            updates["term_tgt_origin"] = f"agent:glossary_curator:{today}"

        # Check and update notes
        if notes is not None:
            if entry.notes and entry.notes_origin == "human" and not allow_overwrite:
                message = f"Glossary entry '{term_src}' has human-authored notes."
                raise ValueError(message)
            updates["notes"] = notes
            updates["notes_origin"] = f"agent:glossary_curator:{today}"

        if updates:
            updated_entry = entry.model_copy(update=updates)
            self.glossary[entry_index] = updated_entry
            # Track update count
            if not hasattr(self, "_glossary_update_count"):
                self._glossary_update_count = 0
            self._glossary_update_count += 1
            await self._write_glossary()

    async def _write_glossary(self) -> None:
        """Persist the current glossary to disk."""
        path = self.metadata_dir / "glossary.jsonl"
        lines = [orjson.dumps(entry.model_dump()).decode("utf-8") for entry in self.glossary]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def update_route_synopsis(self, route_id: str, synopsis: str, *, allow_overwrite: bool = False) -> None:
        """Update the synopsis for *route_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite human-authored data without permission.
        """
        from datetime import date

        route = self.get_route(route_id)
        if route.synopsis and route.synopsis_origin == "human" and not allow_overwrite:
            message = f"Route '{route_id}' has a human-authored synopsis."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_route = route.model_copy(
            update={"synopsis": synopsis, "synopsis_origin": f"agent:route_detailer:{today}"}
        )
        self.routes[route_id] = updated_route
        await self._write_routes()

    async def update_route_characters(
        self, route_id: str, character_ids: list[str], *, allow_overwrite: bool = False
    ) -> None:
        """Update the primary characters for *route_id* and persist to disk.

        Raises:
            ValueError: If attempting to overwrite human-authored data without permission.
        """
        from datetime import date

        route = self.get_route(route_id)
        if route.primary_characters and route.primary_characters_origin == "human" and not allow_overwrite:
            message = f"Route '{route_id}' has human-authored primary characters."
            raise ValueError(message)

        today = date.today().isoformat()
        updated_route = route.model_copy(
            update={
                "primary_characters": character_ids,
                "primary_characters_origin": f"agent:route_detailer:{today}",
            }
        )
        self.routes[route_id] = updated_route
        await self._write_routes()

    async def _write_routes(self) -> None:
        """Persist the current route metadata to disk."""
        path = self.metadata_dir / "routes.jsonl"
        lines = [orjson.dumps(self.routes[key].model_dump()).decode("utf-8") for key in sorted(self.routes)]
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
