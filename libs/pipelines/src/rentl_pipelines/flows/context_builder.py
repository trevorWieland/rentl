"""Context Builder pipeline for enriching game metadata.

This pipeline orchestrates all context detailer subagents to enrich:
- Scene metadata (summaries, tags, characters, locations)
- Character metadata (target names, pronouns, personality notes)
- Location metadata (target names, descriptions)
- Glossary entries (terminology management)
- Route metadata (synopsis, primary characters)
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast

import anyio
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.backends.coordinator import create_coordinator_agent
from rentl_agents.subagents.character_detailer import create_character_detailer_subagent
from rentl_agents.subagents.glossary_curator import create_glossary_curator_subagent
from rentl_agents.subagents.location_detailer import create_location_detailer_subagent
from rentl_agents.subagents.route_detailer import create_route_detailer_subagent
from rentl_agents.subagents.scene_detailer import create_scene_detailer_subagent
from rentl_agents.tools.stats import build_stats_tools
from rentl_core.context.project import load_project_context
from rentl_core.util.logging import get_logger

from rentl_pipelines.flows.utils import SupportsAinvoke, invoke_with_interrupts

logger = get_logger(__name__)

_CONTEXT_BUILDER_SYSTEM_PROMPT = """You are the Context Builder coordinator.

Use the task() tool to run subagents that enrich scenes, characters, locations, glossary, and routes.
Run each subagent once unless work is already complete. Keep responses concise and focused on progress.
Before scheduling a scene, call get_scene_completion; skip scenes where all fields are yes.
Do not call filesystem or other default tools; only use task() and stats tools."""


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
    decision_handler: Callable[[list[str]], list[str]] | None = None,
    thread_id: str | None = None,
) -> ContextBuilderResult:
    """Run the Context Builder pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        allow_overwrite: Allow overwriting existing metadata.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.

    Returns:
        ContextBuilderResult: Statistics about what was enriched.
    """
    logger.info("Starting Context Builder pipeline for %s", project_path)
    context = await load_project_context(project_path)

    scene_ids = sorted(context.scenes.keys())
    character_ids = sorted(context.characters.keys())
    location_ids = sorted(context.locations.keys())
    route_ids = sorted(context.routes.keys())
    initial_glossary_count = len(context.glossary)

    subagents = [
        create_scene_detailer_subagent(context, allow_overwrite=allow_overwrite),
        create_character_detailer_subagent(context, allow_overwrite=allow_overwrite),
        create_location_detailer_subagent(context, allow_overwrite=allow_overwrite),
        create_glossary_curator_subagent(context, allow_overwrite=allow_overwrite),
        create_route_detailer_subagent(context, allow_overwrite=allow_overwrite),
    ]

    tools = build_stats_tools(context)
    model = get_default_chat_model()
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
    subagent_names = [subagent["name"] for subagent in subagents]
    logger.info("Coordinator starting with subagents: %s", ", ".join(subagent_names))
    logger.info("Coordinator progress tools: %s", ", ".join(tool_names))

    agent = create_coordinator_agent(
        model=model,
        tools=tools,
        subagents=subagents,
        system_prompt=_CONTEXT_BUILDER_SYSTEM_PROMPT,
        interrupt_on={
            "write_scene_summary": True,
            "write_scene_tags": True,
            "write_primary_characters": True,
            "write_scene_locations": True,
            "update_character_name_tgt": True,
            "update_character_pronouns": True,
            "update_character_notes": True,
            "update_location_name_tgt": True,
            "update_location_description": True,
            "add_glossary_entry": True,
            "update_glossary_entry": True,
            "update_route_synopsis": True,
            "update_route_characters": True,
        },
        checkpointer=MemorySaver(),
    )

    available = "\n".join(subagent["name"] for subagent in subagents)
    user_prompt = (
        "Enrich all metadata for this project.\n"
        "Process every scene, character, location, glossary, and route. "
        "Use task() to run the appropriate subagent and pass the target id in your message.\n\n"
        f"Scenes: {', '.join(scene_ids)}\n"
        f"Characters: {', '.join(character_ids)}\n"
        f"Locations: {', '.join(location_ids)}\n"
        f"Routes: {', '.join(route_ids)}\n\n"
        f"Available subagents:\n{available}\n\n"
        "Use get_context_status and get_scene_completion to track progress. End when all entities are detailed."
    )

    await invoke_with_interrupts(
        cast(SupportsAinvoke, agent),
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=thread_id,
    )

    result = ContextBuilderResult(
        scenes_detailed=len(scene_ids),
        characters_detailed=len(character_ids),
        locations_detailed=len(location_ids),
        glossary_entries_added=max(len(context.glossary) - initial_glossary_count, 0),
        glossary_entries_updated=context._glossary_update_count,
        routes_detailed=len(route_ids),
    )

    logger.info("Context Builder pipeline complete: %s", result)
    return result


def run_context_builder(
    project_path: Path,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[str]] | None = None,
    thread_id: str | None = None,
) -> ContextBuilderResult:
    """Run the Context Builder pipeline to enrich all game metadata.

    Args:
        project_path: Path to the game project.
        allow_overwrite: Allow overwriting existing metadata.
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
            decision_handler=decision_handler,
            thread_id=thread_id,
        )
    )
