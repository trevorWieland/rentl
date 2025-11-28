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
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field
from rentl_agents.hitl.checkpoints import get_default_checkpointer
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

from rentl_pipelines.flows.utils import (
    PIPELINE_FAILURE_EXCEPTIONS,
    PipelineError,
    run_with_retries,
)

logger = get_logger(__name__)


class ContextBuilderResult(BaseModel):
    """Results from the Context Builder pipeline."""

    scenes_detailed: int = Field(description="Number of scenes detailed.")
    characters_detailed: int = Field(description="Number of characters detailed.")
    locations_detailed: int = Field(description="Number of locations detailed.")
    glossary_entries_added: int = Field(description="Number of glossary entries added.")
    glossary_entries_updated: int = Field(description="Number of glossary entries updated.")
    routes_detailed: int = Field(description="Number of routes detailed.")
    errors: list[PipelineError] = Field(default_factory=list, description="Errors encountered during processing.")


async def _run_context_builder_async(
    project_path: Path,
    *,
    allow_overwrite: bool = False,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
    progress_cb: Callable[[str, str], None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> ContextBuilderResult:
    """Run the Context Builder pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        allow_overwrite: Allow overwriting existing metadata.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent subagent runs.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.
        progress_cb: Optional callback invoked as (event, entity_id) per subagent start.
        checkpointer: Optional LangGraph checkpoint saver to reuse (defaults to SQLite).
        checkpointer: Optional LangGraph checkpoint saver to reuse (defaults to SQLite).
        checkpointer: Optional LangGraph checkpoint saver to reuse (defaults to SQLite).

    Returns:
        ContextBuilderResult: Statistics about what was enriched.
    """
    logger.info("Starting Context Builder pipeline for %s", project_path)
    context = await load_project_context(project_path)
    effective_checkpointer = checkpointer or await get_default_checkpointer(project_path / ".rentl" / "checkpoints.db")
    allow_overwrite = mode == "overwrite"
    scenes_to_run = _filter_scenes(context.scenes.values(), mode)
    characters_to_run = _filter_characters(context.characters.values(), mode)
    locations_to_run = _filter_locations(context.locations.values(), mode)
    routes_to_run = _filter_routes(context.routes.values(), mode)

    semaphore = anyio.Semaphore(max(1, concurrency))
    errors: list[PipelineError] = []
    scenes_completed = 0
    characters_completed = 0
    locations_completed = 0
    routes_completed = 0

    base_thread = thread_id or "context"

    def _record_error(stage: str, entity_id: str, exc: BaseException) -> None:
        errors.append(PipelineError(stage=stage, entity_id=entity_id, error=str(exc)))
        logger.error("%s failed for %s: %s", stage, entity_id, exc)
        if progress_cb:
            progress_cb(f"{stage}_error", entity_id)

    async def _bounded(stage: str, entity_id: str, coro_factory: Callable[[], Awaitable[object]]) -> None:
        async with semaphore:
            try:
                await run_with_retries(
                    coro_factory,
                    on_retry=lambda attempt, exc: logger.warning(
                        "Retrying %s for %s (attempt %d): %s", stage, entity_id, attempt + 1, exc
                    ),
                )
                if progress_cb:
                    progress_cb(f"{stage}_done", entity_id)
                nonlocal scenes_completed, characters_completed, locations_completed, routes_completed
                if stage == "scene_detail":
                    scenes_completed += 1
                elif stage == "character_detail":
                    characters_completed += 1
                elif stage == "location_detail":
                    locations_completed += 1
                elif stage == "route_detail":
                    routes_completed += 1
            except PIPELINE_FAILURE_EXCEPTIONS as exc:
                _record_error(stage, entity_id, exc)

    async with anyio.create_task_group() as tg:
        for sid in scenes_to_run:
            if progress_cb:
                progress_cb("scene_detail_start", sid)
            tg.start_soon(
                _bounded,
                "scene_detail",
                sid,
                lambda sid=sid: detail_scene(
                    context,
                    sid,
                    allow_overwrite=allow_overwrite,
                    checkpointer=effective_checkpointer,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:scene:{sid}",
                ),
            )

    async with anyio.create_task_group() as tg:
        for cid in characters_to_run:
            if progress_cb:
                progress_cb("character_detail_start", cid)
            tg.start_soon(
                _bounded,
                "character_detail",
                cid,
                lambda cid=cid: detail_character(
                    context,
                    cid,
                    allow_overwrite=allow_overwrite,
                    checkpointer=effective_checkpointer,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:character:{cid}",
                ),
            )

    async with anyio.create_task_group() as tg:
        for lid in locations_to_run:
            if progress_cb:
                progress_cb("location_detail_start", lid)
            tg.start_soon(
                _bounded,
                "location_detail",
                lid,
                lambda lid=lid: detail_location(
                    context,
                    lid,
                    allow_overwrite=allow_overwrite,
                    checkpointer=effective_checkpointer,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:location:{lid}",
                ),
            )

    glossary_result: GlossaryDetailResult | None = None
    try:
        glossary_result = await detail_glossary(
            context,
            allow_overwrite=allow_overwrite,
            checkpointer=effective_checkpointer,
            decision_handler=decision_handler,
            thread_id=f"{base_thread}:glossary",
        )
    except Exception as exc:
        logger.warning("Glossary curation failed: %s", exc)

    async with anyio.create_task_group() as tg:
        for rid in routes_to_run:
            if progress_cb:
                progress_cb("route_detail_start", rid)
            tg.start_soon(
                _bounded,
                "route_detail",
                rid,
                lambda rid=rid: detail_route(
                    context,
                    rid,
                    allow_overwrite=allow_overwrite,
                    checkpointer=effective_checkpointer,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:route:{rid}",
                ),
            )

    result = ContextBuilderResult(
        scenes_detailed=scenes_completed,
        characters_detailed=characters_completed,
        locations_detailed=locations_completed,
        glossary_entries_added=(glossary_result.entries_added if glossary_result else 0),
        glossary_entries_updated=(glossary_result.entries_updated if glossary_result else 0),
        routes_detailed=routes_completed,
        errors=errors,
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
    progress_cb: Callable[[str, str], None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> ContextBuilderResult:
    """Run the Context Builder pipeline to enrich all game metadata.

    Args:
        project_path: Path to the game project.
        allow_overwrite: Allow overwriting existing metadata.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent subagent runs.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.
        progress_cb: Optional callback invoked as (event, entity_id) per subagent start.
        checkpointer: Optional LangGraph checkpoint saver to reuse (defaults to SQLite).

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
            progress_cb=progress_cb,
            checkpointer=checkpointer,
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
