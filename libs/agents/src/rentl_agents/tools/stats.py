"""Shared stats tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext


def _get_completion_ratio(completed: int, total: int) -> float:
    """Return completion ratio with zero guard."""
    return round(completed / total, 3) if total else 0.0


def get_context_status(context: ProjectContext) -> str:
    """Summarize context completion across scenes, characters, locations, and routes.

    Returns:
        str: Completion summary suitable for quick progress checks.
    """
    scenes = len(context.scenes)
    characters = len(context.characters)
    locations = len(context.locations)
    routes = len(context.routes)

    summaries = sum(1 for s in context.scenes.values() if s.annotations.summary)
    tags = sum(1 for s in context.scenes.values() if s.annotations.tags)
    primary_chars = sum(1 for s in context.scenes.values() if s.annotations.primary_characters)
    locs = sum(1 for s in context.scenes.values() if s.annotations.locations)

    return (
        "Context status:\n"
        f"- Scenes: {scenes} total | summaries {summaries}/{scenes} ({_get_completion_ratio(summaries, scenes)}) | "
        f"tags {tags}/{scenes} ({_get_completion_ratio(tags, scenes)}) | "
        f"primary_characters {primary_chars}/{scenes} ({_get_completion_ratio(primary_chars, scenes)}) | "
        f"locations {locs}/{scenes} ({_get_completion_ratio(locs, scenes)})\n"
        f"- Characters: {characters} total\n"
        f"- Locations: {locations} total\n"
        f"- Routes: {routes} total\n"
    )


def get_scene_completion(context: ProjectContext, scene_id: str) -> str:
    """Return detailed completion for a specific scene.

    Returns:
        str: Human-readable scene completion status.
    """
    scene = context.get_scene(scene_id)
    annotations = scene.annotations
    parts = [
        f"Scene {scene_id}:",
        f"- Summary: {'yes' if annotations.summary else 'no'}",
        f"- Tags: {'yes' if annotations.tags else 'no'}",
        f"- Primary Characters: {'yes' if annotations.primary_characters else 'no'}",
        f"- Locations: {'yes' if annotations.locations else 'no'}",
    ]
    return "\n".join(parts)


def get_character_completion(context: ProjectContext, character_id: str) -> str:
    """Return completion for a specific character.

    Returns:
        str: Human-readable character completion status.
    """
    character = context.get_character(character_id)
    parts = [
        f"Character {character_id}:",
        f"- Source Name: {'yes' if character.name_src else 'no'}",
        f"- Target Name: {'yes' if character.name_tgt else 'no'}",
        f"- Pronouns: {'yes' if character.pronouns else 'no'}",
        f"- Notes: {'yes' if character.notes else 'no'}",
    ]
    return "\n".join(parts)


async def get_translation_progress(context: ProjectContext, scene_id: str) -> str:
    """Report translation progress for a scene.

    Returns:
        str: Translation progress summary.
    """
    await context._load_translations(scene_id)
    total_lines = len(await context.load_scene_lines(scene_id))
    translated = context.get_translated_line_count(scene_id)
    return (
        f"Scene {scene_id}: {translated}/{total_lines} lines translated "
        f"({_get_completion_ratio(translated, total_lines)})"
    )


def get_route_progress(context: ProjectContext, route_id: str) -> str:
    """Report route metadata completion.

    Returns:
        str: Route completion summary.
    """
    route = context.get_route(route_id)
    synopsis_done = bool(route.synopsis)
    chars_done = bool(route.primary_characters)
    parts = [
        f"Route {route_id}:",
        f"- Synopsis: {'yes' if synopsis_done else 'no'}",
        f"- Primary Characters: {'yes' if chars_done else 'no'}",
        f"- Scenes: {len(route.scene_ids)} linked",
    ]
    return "\n".join(parts)
