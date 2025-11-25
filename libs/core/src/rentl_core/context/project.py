"""Helpers for loading and mutating project metadata."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

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
from rentl_core.io.writer import write_translation
from rentl_core.model.character import CharacterMetadata
from rentl_core.model.game import GameMetadata
from rentl_core.model.glossary import GlossaryEntry
from rentl_core.model.line import SourceLine, TranslatedLine
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneMetadata


class ProjectContext:
    """In-memory representation of a rentl project with concurrent access support."""

    def __init__(
        self,
        project_path: Path,
        game: GameMetadata,
        characters: dict[str, CharacterMetadata],
        glossary: list[GlossaryEntry],
        locations: dict[str, LocationMetadata],
        routes: dict[str, RouteMetadata],
        scenes: dict[str, SceneMetadata],
        metadata_dir: Path,
        scenes_dir: Path,
        context_docs_dir: Path,
        output_dir: Path,
    ) -> None:
        """Initialize ProjectContext with metadata and locking infrastructure.

        Args:
            project_path: Root path of the project.
            game: Game metadata.
            characters: Character metadata by ID.
            glossary: List of glossary entries.
            locations: Location metadata by ID.
            routes: Route metadata by ID.
            scenes: Scene metadata by ID.
            metadata_dir: Path to metadata directory.
            scenes_dir: Path to scenes directory.
            context_docs_dir: Path to context docs directory.
            output_dir: Path to project output directory (translations/reports).
        """
        self.project_path = project_path
        self.game = game
        self.characters = characters
        self.glossary = glossary
        self.locations = locations
        self.routes = routes
        self.scenes = scenes
        self.metadata_dir = metadata_dir
        self.scenes_dir = scenes_dir
        self.context_docs_dir = context_docs_dir
        self.output_dir = output_dir

        # Entity-level locks for concurrent access
        self._scene_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._character_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._location_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._route_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._glossary_lock = asyncio.Lock()

        # Track recent updates for conflict detection: (entity_type, entity_id, field_name) -> timestamp
        self._recent_updates: dict[tuple[str, str, str], float] = {}

        # Track glossary update count for subagent result reporting
        self._glossary_update_count = 0

        # Translation state (in-memory, persisted on every update)
        self._translations: dict[str, dict[str, TranslatedLine]] = {}

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

    async def read_style_guide(self) -> str:
        """Read the project style guide.

        Returns:
            str: Style guide content or fallback note if missing.
        """
        path = anyio.Path(self.metadata_dir / "style_guide.md")
        if not await path.exists():
            return "No style guide found."
        return await path.read_text()

    def get_ui_config(self) -> dict[str, Any]:
        """Return UI configuration from game metadata (e.g., max line length)."""
        ui = self.game.ui or {}
        return dict(ui)

    async def set_scene_summary(
        self,
        scene_id: str,
        summary: str,
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the stored summary for *scene_id* with conflict detection.

        Args:
            scene_id: Scene identifier.
            summary: New summary text.
            origin: Provenance string (e.g., "agent:scene_detailer:2024-11-23").
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._scene_locks[scene_id]:
            scene = self.get_scene(scene_id)
            current_summary = scene.annotations.summary

            # Check for recent concurrent update
            update_key = ("scene", scene_id, "summary")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            # Conflict detected: another agent updated this recently
            if time_since_update < conflict_threshold_seconds and current_summary:
                return f"""CONCURRENT UPDATE DETECTED

Summary for scene '{scene_id}' was updated {time_since_update:.1f}s ago.

Current summary: {current_summary}

Your proposed summary: {summary}

Review and retry if your update is still needed."""

            # No conflict - proceed with update
            updated_annotations = scene.annotations.model_copy(update={"summary": summary, "summary_origin": origin})
            updated_scene = scene.model_copy(update={"annotations": updated_annotations})
            self.scenes[scene_id] = updated_scene
            self._recent_updates[update_key] = time.time()

            # Write to disk immediately (crash-safe)
            await self._write_scenes()

            return f"Successfully updated summary for scene '{scene_id}'"

    async def set_scene_tags(
        self,
        scene_id: str,
        tags: list[str],
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the stored tags for *scene_id* with conflict detection.

        Args:
            scene_id: Scene identifier.
            tags: New tags list.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._scene_locks[scene_id]:
            scene = self.get_scene(scene_id)
            current_tags = scene.annotations.tags

            update_key = ("scene", scene_id, "tags")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_tags:
                return f"""CONCURRENT UPDATE DETECTED

Tags for scene '{scene_id}' were updated {time_since_update:.1f}s ago.

Current tags: {current_tags}
Your proposed tags: {tags}

Review and retry if your update is still needed."""

            updated_annotations = scene.annotations.model_copy(update={"tags": tags, "tags_origin": origin})
            updated_scene = scene.model_copy(update={"annotations": updated_annotations})
            self.scenes[scene_id] = updated_scene
            self._recent_updates[update_key] = time.time()
            await self._write_scenes()
            return f"Successfully updated tags for scene '{scene_id}'"

    async def set_scene_characters(
        self,
        scene_id: str,
        character_ids: list[str],
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the stored primary characters for *scene_id* with conflict detection.

        Args:
            scene_id: Scene identifier.
            character_ids: List of primary character IDs.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._scene_locks[scene_id]:
            scene = self.get_scene(scene_id)
            current_characters = scene.annotations.primary_characters

            update_key = ("scene", scene_id, "primary_characters")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_characters:
                return f"""CONCURRENT UPDATE DETECTED

Primary characters for scene '{scene_id}' were updated {time_since_update:.1f}s ago.

Current: {current_characters}
Your proposed: {character_ids}

Review and retry if your update is still needed."""

            updated_annotations = scene.annotations.model_copy(
                update={"primary_characters": character_ids, "primary_characters_origin": origin}
            )
            updated_scene = scene.model_copy(update={"annotations": updated_annotations})
            self.scenes[scene_id] = updated_scene
            self._recent_updates[update_key] = time.time()
            await self._write_scenes()
            return f"Successfully updated primary characters for scene '{scene_id}'"

    async def set_scene_locations(
        self,
        scene_id: str,
        location_ids: list[str],
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the stored locations for *scene_id* with conflict detection.

        Args:
            scene_id: Scene identifier.
            location_ids: List of location IDs.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._scene_locks[scene_id]:
            scene = self.get_scene(scene_id)
            current_locations = scene.annotations.locations

            update_key = ("scene", scene_id, "locations")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_locations:
                return f"""CONCURRENT UPDATE DETECTED

Locations for scene '{scene_id}' were updated {time_since_update:.1f}s ago.

Current: {current_locations}
Your proposed: {location_ids}

Review and retry if your update is still needed."""

            updated_annotations = scene.annotations.model_copy(
                update={"locations": location_ids, "locations_origin": origin}
            )
            updated_scene = scene.model_copy(update={"annotations": updated_annotations})
            self.scenes[scene_id] = updated_scene
            self._recent_updates[update_key] = time.time()
            await self._write_scenes()
            return f"Successfully updated locations for scene '{scene_id}'"

    async def _write_scenes(self) -> None:
        """Persist the current scene metadata to disk."""
        path = self.metadata_dir / "scenes.jsonl"
        lines = [orjson.dumps(self.scenes[key].model_dump()).decode("utf-8") for key in sorted(self.scenes)]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def update_character_name_tgt(
        self,
        character_id: str,
        name_tgt: str,
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the target language name for *character_id* with conflict detection.

        Args:
            character_id: Character identifier.
            name_tgt: New target language name.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._character_locks[character_id]:
            character = self.get_character(character_id)
            current_name = character.name_tgt

            update_key = ("character", character_id, "name_tgt")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_name:
                return f"""CONCURRENT UPDATE DETECTED

Name for character '{character_id}' was updated {time_since_update:.1f}s ago.

Current: {current_name}
Your proposed: {name_tgt}

Review and retry if your update is still needed."""

            updated_character = character.model_copy(update={"name_tgt": name_tgt, "name_tgt_origin": origin})
            self.characters[character_id] = updated_character
            self._recent_updates[update_key] = time.time()
            await self._write_characters()
            return f"Successfully updated name for character '{character_id}'"

    async def update_character_pronouns(
        self,
        character_id: str,
        pronouns: str,
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update pronoun preferences for *character_id* with conflict detection.

        Args:
            character_id: Character identifier.
            pronouns: New pronoun preferences.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._character_locks[character_id]:
            character = self.get_character(character_id)
            current_pronouns = character.pronouns

            update_key = ("character", character_id, "pronouns")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_pronouns:
                return f"""CONCURRENT UPDATE DETECTED

Pronouns for character '{character_id}' were updated {time_since_update:.1f}s ago.

Current: {current_pronouns}
Your proposed: {pronouns}

Review and retry if your update is still needed."""

            updated_character = character.model_copy(update={"pronouns": pronouns, "pronouns_origin": origin})
            self.characters[character_id] = updated_character
            self._recent_updates[update_key] = time.time()
            await self._write_characters()
            return f"Successfully updated pronouns for character '{character_id}'"

    async def update_character_notes(
        self,
        character_id: str,
        notes: str,
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update character notes for *character_id* with conflict detection.

        Args:
            character_id: Character identifier.
            notes: New character notes/bio.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._character_locks[character_id]:
            character = self.get_character(character_id)
            current_notes = character.notes

            update_key = ("character", character_id, "notes")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_notes:
                return f"""CONCURRENT UPDATE DETECTED

Notes for character '{character_id}' were updated {time_since_update:.1f}s ago.

Current: {current_notes}
Your proposed: {notes}

Review and retry if your update is still needed."""

            updated_character = character.model_copy(update={"notes": notes, "notes_origin": origin})
            self.characters[character_id] = updated_character
            self._recent_updates[update_key] = time.time()
            await self._write_characters()
            return f"Successfully updated notes for character '{character_id}'"

    async def _write_characters(self) -> None:
        """Persist the current character metadata to disk."""
        path = self.metadata_dir / "characters.jsonl"
        lines = [orjson.dumps(self.characters[key].model_dump()).decode("utf-8") for key in sorted(self.characters)]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def add_character(
        self,
        character_id: str,
        name_src: str,
        *,
        name_tgt: str | None = None,
        pronouns: str | None = None,
        notes: str | None = None,
        origin: str,
    ) -> str:
        """Add a new character entry with provenance tracking.

        Args:
            character_id: New character identifier.
            name_src: Source-language name.
            name_tgt: Optional target-language name.
            pronouns: Optional pronouns/notes.
            notes: Optional character notes.
            origin: Provenance string to apply to all provided fields.

        Returns:
            Status message.
        """
        if character_id in self.characters:
            return f"Character '{character_id}' already exists."

        new_character = CharacterMetadata(
            id=character_id,
            name_src=name_src,
            name_src_origin=origin,
            name_tgt=name_tgt,
            name_tgt_origin=origin if name_tgt else None,
            pronouns=pronouns,
            pronouns_origin=origin if pronouns else None,
            notes=notes,
            notes_origin=origin if notes else None,
        )
        self.characters[character_id] = new_character
        await self._write_characters()
        return f"Added character '{character_id}'"

    async def update_location_name_tgt(
        self,
        location_id: str,
        name_tgt: str,
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the target language name for *location_id* with conflict detection.

        Args:
            location_id: Location identifier.
            name_tgt: New target language name.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._location_locks[location_id]:
            location = self.get_location(location_id)
            current_name = location.name_tgt

            update_key = ("location", location_id, "name_tgt")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_name:
                return f"""CONCURRENT UPDATE DETECTED

Name for location '{location_id}' was updated {time_since_update:.1f}s ago.

Current: {current_name}
Your proposed: {name_tgt}

Review and retry if your update is still needed."""

            updated_location = location.model_copy(update={"name_tgt": name_tgt, "name_tgt_origin": origin})
            self.locations[location_id] = updated_location
            self._recent_updates[update_key] = time.time()
            await self._write_locations()
            return f"Successfully updated name for location '{location_id}'"

    async def update_location_description(
        self,
        location_id: str,
        description: str,
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the description for *location_id* with conflict detection.

        Args:
            location_id: Location identifier.
            description: New description text.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._location_locks[location_id]:
            location = self.get_location(location_id)
            current_description = location.description

            update_key = ("location", location_id, "description")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_description:
                return f"""CONCURRENT UPDATE DETECTED

Description for location '{location_id}' was updated {time_since_update:.1f}s ago.

Current: {current_description}
Your proposed: {description}

Review and retry if your update is still needed."""

            updated_location = location.model_copy(update={"description": description, "description_origin": origin})
            self.locations[location_id] = updated_location
            self._recent_updates[update_key] = time.time()
            await self._write_locations()
            return f"Successfully updated description for location '{location_id}'"

    async def _write_locations(self) -> None:
        """Persist the current location metadata to disk."""
        path = self.metadata_dir / "locations.jsonl"
        lines = [orjson.dumps(self.locations[key].model_dump()).decode("utf-8") for key in sorted(self.locations)]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def add_location(
        self,
        location_id: str,
        name_src: str,
        *,
        name_tgt: str | None = None,
        description: str | None = None,
        origin: str,
    ) -> str:
        """Add a new location entry with provenance tracking.

        Args:
            location_id: New location identifier.
            name_src: Source-language name.
            name_tgt: Optional target-language name.
            description: Optional description.
            origin: Provenance string to apply to provided fields.

        Returns:
            Status message.
        """
        if location_id in self.locations:
            return f"Location '{location_id}' already exists."

        new_location = LocationMetadata(
            id=location_id,
            name_src=name_src,
            name_src_origin=origin,
            name_tgt=name_tgt,
            name_tgt_origin=origin if name_tgt else None,
            description=description,
            description_origin=origin if description else None,
        )
        self.locations[location_id] = new_location
        await self._write_locations()
        return f"Added location '{location_id}'"

    async def add_glossary_entry(
        self,
        term_src: str,
        term_tgt: str,
        notes: str | None,
        origin: str,
    ) -> str:
        """Add a new glossary entry and persist to disk.

        Args:
            term_src: Source language term.
            term_tgt: Target language term.
            notes: Optional translation notes.
            origin: Provenance string.

        Returns:
            str: Success message or error if entry already exists.
        """
        async with self._glossary_lock:
            # Check if entry already exists
            for entry in self.glossary:
                if entry.term_src == term_src:
                    return f"Glossary entry for '{term_src}' already exists. Use update_glossary_entry instead."

            new_entry = GlossaryEntry(
                term_src=term_src,
                term_src_origin=origin,
                term_tgt=term_tgt,
                term_tgt_origin=origin,
                notes=notes,
                notes_origin=origin if notes else None,
            )
            self.glossary.append(new_entry)
            await self._write_glossary()
            return f"Successfully added glossary entry: {term_src} → {term_tgt}"

    async def update_glossary_entry(
        self,
        term_src: str,
        term_tgt: str | None,
        notes: str | None,
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update an existing glossary entry with conflict detection.

        Args:
            term_src: Source term to update.
            term_tgt: New target term (optional, keeps existing if None).
            notes: New notes (optional, keeps existing if None).
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message, conflict notification, or error if not found.
        """
        async with self._glossary_lock:
            # Find the entry
            entry_index = None
            for i, entry in enumerate(self.glossary):
                if entry.term_src == term_src:
                    entry_index = i
                    break

            if entry_index is None:
                return f"Glossary entry for '{term_src}' not found. Use add_glossary_entry to create it."

            entry = self.glossary[entry_index]
            updates = {}

            # Check for recent updates
            update_key = ("glossary", term_src, "entry")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds:
                return f"""CONCURRENT UPDATE DETECTED

Glossary entry '{term_src}' was updated {time_since_update:.1f}s ago.

Current: {entry.term_tgt} ({entry.notes or "no notes"})
Your proposed: {term_tgt or entry.term_tgt} ({notes or entry.notes or "no notes"})

Review and retry if your update is still needed."""

            # Build updates
            if term_tgt is not None:
                updates["term_tgt"] = term_tgt
                updates["term_tgt_origin"] = origin

            if notes is not None:
                updates["notes"] = notes
                updates["notes_origin"] = origin

            if updates:
                updated_entry = entry.model_copy(update=updates)
                self.glossary[entry_index] = updated_entry
                self._glossary_update_count += 1
                self._recent_updates[update_key] = time.time()
                await self._write_glossary()
            return f"Successfully updated glossary entry: {term_src}"

        return f"No changes to glossary entry: {term_src}"

    async def delete_glossary_entry(self, term_src: str) -> str:
        """Delete a glossary entry if present.

        Args:
            term_src: Source term to delete.

        Returns:
            Status message.
        """
        async with self._glossary_lock:
            remaining = [entry for entry in self.glossary if entry.term_src != term_src]
            if len(remaining) == len(self.glossary):
                return f"Glossary entry for '{term_src}' not found."

            self.glossary = remaining
            await self._write_glossary()
            return f"Deleted glossary entry: {term_src}"

    async def _write_glossary(self) -> None:
        """Persist the current glossary to disk."""
        path = self.metadata_dir / "glossary.jsonl"
        lines = [orjson.dumps(entry.model_dump()).decode("utf-8") for entry in self.glossary]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def update_route_synopsis(
        self,
        route_id: str,
        synopsis: str,
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the synopsis for *route_id* with conflict detection.

        Args:
            route_id: Route identifier.
            synopsis: New synopsis text.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._route_locks[route_id]:
            route = self.get_route(route_id)
            current_synopsis = route.synopsis

            update_key = ("route", route_id, "synopsis")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_synopsis:
                return f"""CONCURRENT UPDATE DETECTED

Synopsis for route '{route_id}' was updated {time_since_update:.1f}s ago.

Current: {current_synopsis}
Your proposed: {synopsis}

Review and retry if your update is still needed."""

            updated_route = route.model_copy(update={"synopsis": synopsis, "synopsis_origin": origin})
            self.routes[route_id] = updated_route
            self._recent_updates[update_key] = time.time()
            await self._write_routes()
            return f"Successfully updated synopsis for route '{route_id}'"

    async def update_route_characters(
        self,
        route_id: str,
        character_ids: list[str],
        origin: str,
        *,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Update the primary characters for *route_id* with conflict detection.

        Args:
            route_id: Route identifier.
            character_ids: List of primary character IDs.
            origin: Provenance string.
            conflict_threshold_seconds: Time window for conflict detection (default 30s).

        Returns:
            str: Success message or conflict notification.
        """
        async with self._route_locks[route_id]:
            route = self.get_route(route_id)
            current_characters = route.primary_characters

            update_key = ("route", route_id, "primary_characters")
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            if time_since_update < conflict_threshold_seconds and current_characters:
                return f"""CONCURRENT UPDATE DETECTED

Primary characters for route '{route_id}' were updated {time_since_update:.1f}s ago.

Current: {current_characters}
Your proposed: {character_ids}

Review and retry if your update is still needed."""

            updated_route = route.model_copy(
                update={"primary_characters": character_ids, "primary_characters_origin": origin}
            )
            self.routes[route_id] = updated_route
            self._recent_updates[update_key] = time.time()
            await self._write_routes()
            return f"Successfully updated primary characters for route '{route_id}'"

    async def _write_routes(self) -> None:
        """Persist the current route metadata to disk."""
        path = self.metadata_dir / "routes.jsonl"
        lines = [orjson.dumps(self.routes[key].model_dump()).decode("utf-8") for key in sorted(self.routes)]
        async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
            await stream.write("\n".join(lines) + "\n")

    async def _load_translations(self, scene_id: str) -> None:
        """Load translations for a scene into memory if not already loaded."""
        if scene_id in self._translations:
            return

        translations_path = self.output_dir / "translations" / f"{scene_id}.jsonl"
        translations: dict[str, TranslatedLine] = {}

        if translations_path.exists():
            async with await anyio.open_file(translations_path, "rb") as stream:
                async for raw_line in stream:
                    line = raw_line.rstrip(b"\n")
                    if not line:
                        continue
                    data = orjson.loads(line)
                    translated_line = TranslatedLine.model_validate(data)
                    translations[translated_line.id] = translated_line

        self._translations[scene_id] = translations

    def get_translated_line_count(self, scene_id: str) -> int:
        """Return the number of translated lines tracked for a scene."""
        return len(self._translations.get(scene_id, {}))

    async def record_translation(
        self,
        scene_id: str,
        translation: TranslatedLine,
        *,
        allow_overwrite: bool = False,
        conflict_threshold_seconds: float = 30.0,
    ) -> str:
        """Persist a translated line with conflict detection and provenance enforcement.

        Returns:
            str: Status message indicating success or conflict/overwrite guidance.
        """
        await self._load_translations(scene_id)

        async with self._scene_locks[scene_id]:
            translations = self._translations.setdefault(scene_id, {})
            update_key = ("translation", scene_id, translation.id)
            last_update = self._recent_updates.get(update_key, 0.0)
            time_since_update = time.time() - last_update

            existing = translations.get(translation.id)
            if existing and not allow_overwrite:
                return f"Translation for line '{translation.id}' already exists. Set allow_overwrite to replace."

            if existing and time_since_update < conflict_threshold_seconds:
                return (
                    f"CONCURRENT UPDATE DETECTED\n\nLine '{translation.id}' was updated {time_since_update:.1f}s ago.\n"
                    f"Current: {existing.text_tgt}\nProposed: {translation.text_tgt}\n"
                    "Review and retry if overwrite is still needed."
                )

            translations[translation.id] = translation
            self._recent_updates[update_key] = time.time()

            await self._write_translations(scene_id)
            return f"Stored translation for line '{translation.id}'"

    async def _write_translations(self, scene_id: str) -> None:
        """Write translations for a scene to disk in line order."""
        await self._load_translations(scene_id)
        translations = self._translations.get(scene_id, {})
        output_path = self.output_dir / "translations" / f"{scene_id}.jsonl"
        await anyio.Path(output_path.parent).mkdir(parents=True, exist_ok=True)

        # Sort translations by source line order when available
        lines = await self.load_scene_lines(scene_id)
        ordered: list[TranslatedLine] = []
        for line in lines:
            if line.id in translations:
                ordered.append(translations[line.id])

        # Include any extra translations not in source order at the end
        extra = [t for lid, t in translations.items() if lid not in {line.id for line in lines}]
        ordered.extend(sorted(extra, key=lambda t: t.id))

        await write_translation(output_path, ordered)

    async def get_translations(self, scene_id: str) -> list[TranslatedLine]:
        """Return translations for a scene (loads from disk if needed)."""
        await self._load_translations(scene_id)
        return list(self._translations.get(scene_id, {}).values())

    async def add_translation_check(
        self,
        scene_id: str,
        line_id: str,
        check_name: str,
        passed: bool,
        note: str | None,
        origin: str,
    ) -> str:
        """Record a QA check result on a translated line and persist.

        Returns:
            str: Status message after recording the check.
        """
        await self._load_translations(scene_id)
        async with self._scene_locks[scene_id]:
            translations = self._translations.get(scene_id, {})
            if line_id not in translations:
                return f"Translation for line '{line_id}' not found; cannot record check."

            line = translations[line_id]
            checks = dict(line.meta.checks)
            checks[check_name] = (passed, note or "")
            updated_meta = line.meta.model_copy(update={"checks": checks})
            updated_line = line.model_copy(update={"meta": updated_meta, "text_tgt_origin": origin})

            translations[line_id] = updated_line
            self._recent_updates["translation-check", scene_id, line_id] = time.time()
            await self._write_translations(scene_id)
            return f"Recorded {check_name} ({'PASS' if passed else 'FAIL'}) for line '{line_id}'."


async def load_project_context(project_path: Path) -> ProjectContext:
    """Load project metadata and return a :class:`ProjectContext`.

    Returns:
        ProjectContext: Fully populated context.
    """
    metadata_dir = project_path / "metadata"
    scenes_dir = project_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"
    output_dir = project_path / "output"

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
        output_dir=output_dir,
    )
