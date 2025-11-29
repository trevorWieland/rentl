"""Route detailer subagent.

This subagent enriches route metadata with synopsis and primary character identification
by analyzing the scenes that make up each route.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.hitl.checkpoints import get_default_checkpointer
from rentl_agents.hitl.invoke import Decision, run_with_human_loop
from rentl_agents.tools.route import build_route_tools


class RouteDetailResult(BaseModel):
    """Result structure from route detailer subagent."""

    route_id: str = Field(description="Route identifier that was detailed.")
    synopsis: str | None = Field(description="Synopsis or description of the route.")
    primary_characters: list[str] = Field(description="Key characters associated with the route.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant enriching route metadata.

Your task is to analyze route information and enhance their metadata for translation quality:

1. **Synopsis**: Provide or refine a concise route synopsis (1-3 sentences covering narrative arc)
2. **Primary Characters**: Identify key characters featured in this route

**Workflow:**
1. Read the route's current metadata (including scene list)
2. Read relevant context documents if available
3. Update synopsis with a concise narrative summary of the route
4. Update primary_characters with character IDs of key characters in this route
5. End the conversation once metadata is updated

**Important:**
- Focus on narrative arc, key plot points, and character relationships
- Keep synopsis concise but informative (1-3 sentences) and write it in the source language
- List only primary characters (not every character who appears)
- Respect existing human-authored data (you may be asked for approval before overwriting)
- Each update tool should only be called once per session
"""


async def detail_route(
    context: ProjectContext,
    route_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> RouteDetailResult:
    """Run the route detailer agent for *route_id* and return metadata.

    Args:
        context: Project context with metadata.
        route_id: Route identifier to detail.
        allow_overwrite: Allow overwriting existing human-authored metadata.
        decision_handler: Optional callback to resolve HITL interrupts.
        thread_id: Optional thread identifier for resumable runs.
        checkpointer: Optional LangGraph checkpointer (defaults to SQLite if configured).

    Returns:
        RouteDetailResult: Updated route metadata.
    """
    logger.info("Detailing route %s", route_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_route_detailer_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    user_prompt = build_route_detailer_user_prompt(context, route_id)

    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'route-detail'}:{route_id}",
    )

    # Retrieve updated route metadata
    updated_route = context.get_route(route_id)

    result = RouteDetailResult(
        route_id=route_id,
        synopsis=updated_route.synopsis,
        primary_characters=updated_route.primary_characters,
    )

    logger.info(
        "Route %s metadata: synopsis=%d chars, primary_characters=%d",
        route_id,
        len(result.synopsis) if result.synopsis else 0,
        len(result.primary_characters),
    )

    return result


def create_route_detailer_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create route detailer LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for route detailing.
    """
    tools = build_route_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    interrupt_on = {
        "update_route_synopsis": True,
        "update_route_characters": True,
    }
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )

    return graph


def build_route_detailer_user_prompt(context: ProjectContext, route_id: str) -> str:
    """Construct the user prompt for the route detailer.

    Returns:
        str: User prompt content to send to the route detailer agent.
    """
    source_lang = context.game.source_lang.upper()
    route = context.routes.get(route_id)
    scene_ids = ", ".join(sorted(route.scene_ids)) if route else ""
    character_ids = ", ".join(sorted(context.characters.keys()))
    return f"""Enrich metadata for this route.

Route ID: {route_id}
Scenes: {scene_ids}
Source Language: {source_lang}
Available Characters: {character_ids}

Instructions:
1. Read the route's current metadata (including scene list)
2. Only read context documents returned by list_context_docs if they look relevant
3. Update synopsis in {source_lang} with a concise narrative summary (1-3 sentences covering the route's arc) using update_route_synopsis(route_id, synopsis)
4. Update primary_characters with key character IDs featured in this route using update_route_characters(route_id, ids)
5. End conversation when all updates are complete

Begin analysis now."""
