"""Context Builder pipeline for enriching game metadata.

This pipeline orchestrates all context detailer subagents to enrich:
- Scene metadata (summaries, tags, characters, locations)
- Character metadata (target names, pronouns, personality notes)
- Location metadata (target names, descriptions)
- Glossary entries (terminology management)
- Route metadata (synopsis, primary characters)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from functools import partial
from pathlib import Path
from typing import Literal

import anyio
from pydantic import BaseModel, Field
from rentl_agents.subagents.character_detailer import detail_character
from rentl_agents.subagents.glossary_curator import GlossaryDetailResult, detail_glossary
from rentl_agents.subagents.location_detailer import detail_location
from rentl_agents.subagents.route_detailer import detail_route
from rentl_agents.subagents.scene_detailer import detail_scene
from rentl_core.context.project import load_project_context
from rentl_core.model.character import CharacterMetadata
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneMetadata
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


class ContextBuilderResult(BaseModel):
    """Results from the Context Builder pipeline."""

    scenes_detailed: int = Field(description="Number of scenes detailed.")
    characters_detailed: int = Field(description="Number of characters detailed.")
    locations_detailed: int = Field(description="Number of locations detailed.")
    glossary_entries_added: int = Field(description="Number of glossary entries added.")
    glossary_entries_updated: int = Field(description="Number of glossary entries updated.")
    routes_detailed: int = Field(description="Number of routes detailed.")


async def _run_context_builder_async(
    project_path: Path,
    *,
    allow_overwrite: bool = False,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
) -> ContextBuilderResult:
    """Run the Context Builder pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        allow_overwrite: Allow overwriting existing metadata.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent subagent runs.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.

    Returns:
        ContextBuilderResult: Statistics about what was enriched.
    """
    logger.info("Starting Context Builder pipeline for %s", project_path)
    context = await load_project_context(project_path)
    allow_overwrite = mode == "overwrite"
    scenes_to_run = _filter_scenes(context.scenes.values(), mode)
    characters_to_run = _filter_characters(context.characters.values(), mode)
    locations_to_run = _filter_locations(context.locations.values(), mode)
    routes_to_run = _filter_routes(context.routes.values(), mode)

    semaphore = anyio.Semaphore(max(1, concurrency))

    base_thread = thread_id or "context"

    async def _bounded(coro: Awaitable[object]) -> None:
        async with semaphore:
            await coro

    async with anyio.create_task_group() as tg:
        for sid in scenes_to_run:
            tg.start_soon(
                _bounded,
                detail_scene(
                    context,
                    sid,
                    allow_overwrite=allow_overwrite,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:scene:{sid}",
                ),
            )

    async with anyio.create_task_group() as tg:
        for cid in characters_to_run:
            tg.start_soon(
                _bounded,
                detail_character(
                    context,
                    cid,
                    allow_overwrite=allow_overwrite,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:character:{cid}",
                ),
            )

    async with anyio.create_task_group() as tg:
        for lid in locations_to_run:
            tg.start_soon(
                _bounded,
                detail_location(
                    context,
                    lid,
                    allow_overwrite=allow_overwrite,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:location:{lid}",
                ),
            )

    glossary_result: GlossaryDetailResult | None = None
    try:
        glossary_result = await detail_glossary(
            context,
            allow_overwrite=allow_overwrite,
            decision_handler=decision_handler,
            thread_id=f"{base_thread}:glossary",
        )
    except Exception as exc:
        logger.warning("Glossary curation failed: %s", exc)

    async with anyio.create_task_group() as tg:
        for rid in routes_to_run:
            tg.start_soon(
                _bounded,
                detail_route(
                    context,
                    rid,
                    allow_overwrite=allow_overwrite,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:route:{rid}",
                ),
            )

    result = ContextBuilderResult(
        scenes_detailed=len(scenes_to_run),
        characters_detailed=len(characters_to_run),
        locations_detailed=len(locations_to_run),
        glossary_entries_added=(glossary_result.entries_added if glossary_result else 0),
        glossary_entries_updated=(glossary_result.entries_updated if glossary_result else 0),
        routes_detailed=len(routes_to_run),
    )

    logger.info("Context Builder pipeline complete: %s", result)
    return result


def run_context_builder(
    project_path: Path,
    *,
    allow_overwrite: bool = False,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
) -> ContextBuilderResult:
    """Run the Context Builder pipeline to enrich all game metadata.

    Args:
        project_path: Path to the game project.
        allow_overwrite: Allow overwriting existing metadata.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent subagent runs.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.

    Returns:
        ContextBuilderResult: Statistics about what was enriched.
    """
    return anyio.run(
        partial(
            _run_context_builder_async,
            project_path,
            allow_overwrite=allow_overwrite,
            mode=mode,
            concurrency=concurrency,
            decision_handler=decision_handler,
            thread_id=thread_id,
        )
    )


def _filter_scenes(scenes: Iterable[SceneMetadata], mode: Literal["overwrite", "gap-fill", "new-only"]) -> list[str]:
    if mode == "overwrite":
        return sorted(scene.id for scene in scenes)

    def incomplete(scene: SceneMetadata) -> bool:
        ann = scene.annotations
        if mode == "new-only":
            return not any([ann.summary, ann.tags, ann.primary_characters, ann.locations])
        return not all([ann.summary, ann.tags, ann.primary_characters, ann.locations])

    return sorted(scene.id for scene in scenes if incomplete(scene))


def _filter_characters(
    characters: Iterable[CharacterMetadata], mode: Literal["overwrite", "gap-fill", "new-only"]
) -> list[str]:
    if mode == "overwrite":
        return sorted(char.id for char in characters)

    def incomplete(char: CharacterMetadata) -> bool:
        if mode == "new-only":
            return not any([char.name_tgt, char.pronouns, char.notes])
        return not all([char.name_tgt, char.pronouns, char.notes])

    return sorted(char.id for char in characters if incomplete(char))


def _filter_locations(
    locations: Iterable[LocationMetadata], mode: Literal["overwrite", "gap-fill", "new-only"]
) -> list[str]:
    if mode == "overwrite":
        return sorted(loc.id for loc in locations)

    def incomplete(loc: LocationMetadata) -> bool:
        if mode == "new-only":
            return not any([loc.name_tgt, loc.description])
        return not all([loc.name_tgt, loc.description])

    return sorted(loc.id for loc in locations if incomplete(loc))


def _filter_routes(routes: Iterable[RouteMetadata], mode: Literal["overwrite", "gap-fill", "new-only"]) -> list[str]:
    if mode == "overwrite":
        return sorted(route.id for route in routes)

    def incomplete(route: RouteMetadata) -> bool:
        if mode == "new-only":
            return not any([route.synopsis, route.primary_characters])
        return not all([route.synopsis, route.primary_characters])

    return sorted(route.id for route in routes if incomplete(route))
