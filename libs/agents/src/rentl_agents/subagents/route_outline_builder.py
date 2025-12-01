"""Route outline builder subagent."""

from __future__ import annotations

from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import BaseTool, tool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.hitl.checkpoints import get_default_checkpointer
from rentl_agents.hitl.invoke import Decision, run_with_human_loop
from rentl_agents.tools.context_docs import contextdoc_list_all, contextdoc_read_doc
from rentl_agents.tools.route import route_read_entry, route_update_primary_characters, route_update_synopsis


class RouteOutlineResult(BaseModel):
    """Result structure from route outline builder subagent."""

    route_id: str = Field(description="Route identifier that was detailed.")
    synopsis: str | None = Field(description="Synopsis or description of the route.")
    primary_characters: list[str] = Field(description="Key characters associated with the route.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant outlining a route.

Workflow:
1. Read the route's current metadata (including scene list).
2. Write a concise synopsis (1-3 sentences) in the source language.
3. Identify primary characters for the route.
4. Call route_update_synopsis and route_update_primary_characters once each.
5. End when updates are recorded."""


async def build_route_outline(
    context: ProjectContext,
    route_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> RouteOutlineResult:
    """Run the route outline builder for *route_id* and return metadata.

    Returns:
        RouteOutlineResult: Updated route metadata.
    """
    logger.info("Building route outline %s", route_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_route_outline_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    user_prompt = build_route_outline_user_prompt(context, route_id)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'route-outline'}:{route_id}",
    )

    updated_route = context.get_route(route_id)

    return RouteOutlineResult(
        route_id=route_id,
        synopsis=updated_route.synopsis,
        primary_characters=updated_route.primary_characters,
    )


def create_route_outline_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create route outline builder LangChain subagent.

    Returns:
        CompiledStateGraph: Runnable agent graph.
    """
    tools = _build_route_outline_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    interrupt_on = {
        "route_update_synopsis": True,
        "route_update_primary_characters": True,
    }
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )


def build_route_outline_user_prompt(context: ProjectContext, route_id: str) -> str:
    """Construct the user prompt for the route outline builder.

    Returns:
        str: User prompt text.
    """
    source_lang = context.game.source_lang.upper()
    route = context.routes.get(route_id)
    scene_ids = ", ".join(sorted(route.scene_ids)) if route else ""
    character_ids = ", ".join(sorted(context.characters.keys()))
    return f"""Outline this route.

Route ID: {route_id}
Scenes: {scene_ids}
Source Language: {source_lang}
Available Characters: {character_ids}

Instructions:
1. Read the route metadata.
2. Update synopsis in {source_lang} using route_update_synopsis(route_id, synopsis).
3. Update primary_characters using route_update_primary_characters(route_id, ids).
4. End when updates are complete."""


def _build_route_outline_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Return tools for the route outline builder bound to the shared context."""
    updated_synopsis: set[str] = set()
    updated_characters: set[str] = set()
    context_doc_tools = _build_context_doc_tools(context)

    @tool("route_read_entry")
    def route_read_entry_tool(route_id: str) -> str:
        """Return current metadata for this route."""
        return route_read_entry(context, route_id)

    @tool("route_update_synopsis")
    async def route_update_synopsis_tool(route_id: str, synopsis: str) -> str:
        """Update the synopsis for this route.

        Returns:
            str: Status message.
        """
        return await route_update_synopsis(context, route_id, synopsis, updated_synopsis=updated_synopsis)

    @tool("route_update_primary_characters")
    async def route_update_primary_characters_tool(route_id: str, character_ids: list[str]) -> str:
        """Update the primary characters for this route.

        Returns:
            str: Status message.
        """
        return await route_update_primary_characters(
            context, route_id, character_ids, updated_characters=updated_characters
        )

    return [
        route_read_entry_tool,
        *context_doc_tools,
        route_update_synopsis_tool,
        route_update_primary_characters_tool,
    ]


def _build_context_doc_tools(context: ProjectContext) -> list[BaseTool]:
    """Return context doc tools for subagent use."""

    @tool("contextdoc_list_all")
    async def list_context_docs_tool() -> str:
        """Return the available context document names."""
        return await contextdoc_list_all(context)

    @tool("contextdoc_read_doc")
    async def read_context_doc_tool(filename: str) -> str:
        """Return the contents of a context document."""
        return await contextdoc_read_doc(context, filename)

    return [list_context_docs_tool, read_context_doc_tool]
