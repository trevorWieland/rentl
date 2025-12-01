"""Scene location detailer subagent."""

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
from rentl_agents.tools.glossary import glossary_read_entry, glossary_search_term
from rentl_agents.tools.location import (
    location_create_entry,
    location_read_entry,
    location_update_description,
    location_update_name_tgt,
)
from rentl_agents.tools.scene import scene_read_overview, scene_update_locations


class SceneLocationResult(BaseModel):
    """Result structure from scene location detailer subagent."""

    locations: list[str] = Field(description="Location IDs for the scene.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant identifying locations for a scene.

Workflow:
1. Read the scene overview to understand setting/context clues.
2. Decide which location IDs apply (use lowercase IDs).
3. If a needed location is missing, create it with location_create_entry, and enrich name/description if possible.
4. Call scene_update_locations once with the final list of location IDs.
5. Call location_update_name_tgt/location_update_description for locations you can improve.
6. End the conversation when scene locations and any location metadata updates are recorded."""


async def detail_scene_locations(
    context: ProjectContext,
    scene_id: str,
    *,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> SceneLocationResult:
    """Run the scene location detailer for *scene_id* and return location IDs.

    Returns:
        SceneLocationResult: Updated location IDs for the scene.
    """
    logger.info("Detailing scene locations %s", scene_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_scene_location_detailer_subagent(context, checkpointer=effective_checkpointer)

    user_prompt = f"Identify locations for scene {scene_id}. Use scene_update_locations once."
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'scene-locations'}:{scene_id}",
    )

    updated_scene = context.get_scene(scene_id)
    return SceneLocationResult(locations=updated_scene.annotations.locations)


def create_scene_location_detailer_subagent(
    context: ProjectContext,
    *,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create scene location detailer LangChain subagent.

    Returns:
        CompiledStateGraph: Runnable agent graph.
    """
    tools = _build_scene_location_detailer_tools(context)
    model = get_default_chat_model()
    interrupt_on = {
        "scene_update_locations": True,
        "location_update_name_tgt": True,
        "location_update_description": True,
    }
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )


def _build_scene_location_detailer_tools(context: ProjectContext) -> list[BaseTool]:
    """Return tools for the scene location detailer bound to the shared context."""
    written_locations: set[str] = set()
    updated_name_tgt: set[str] = set()
    updated_description: set[str] = set()

    @tool("scene_read_overview")
    async def scene_read_overview_tool(scene_id: str) -> str:
        """Read scene overview with transcript.

        Returns:
            str: Scene overview text.
        """
        return await scene_read_overview(context, scene_id)

    @tool("scene_update_locations")
    async def scene_update_locations_tool(scene_id: str, location_ids: list[str]) -> str:
        """Store locations for this scene.

        Returns:
            str: Status or approval message.
        """
        return await scene_update_locations(context, scene_id, location_ids, written_locations=written_locations)

    @tool("location_read_entry")
    def location_read_entry_tool(location_id: str) -> str:
        """Read location metadata.

        Returns:
            str: Location metadata string.
        """
        return location_read_entry(context, location_id)

    @tool("location_create_entry")
    async def location_create_entry_tool(
        location_id: str, name_src: str, name_tgt: str | None = None, description: str | None = None
    ) -> str:
        """Create a new location entry.

        Returns:
            str: Status message.
        """
        return await location_create_entry(
            context,
            location_id,
            name_src,
            name_tgt=name_tgt,
            description=description,
        )

    @tool("location_update_name_tgt")
    async def location_update_name_tgt_tool(location_id: str, name_tgt: str) -> str:
        """Update target name for a location.

        Returns:
            str: Status message.
        """
        return await location_update_name_tgt(context, location_id, name_tgt, updated_name_tgt=updated_name_tgt)

    @tool("location_update_description")
    async def location_update_description_tool(location_id: str, description: str) -> str:
        """Update description for a location.

        Returns:
            str: Status message.
        """
        return await location_update_description(
            context, location_id, description, updated_description=updated_description
        )

    @tool("glossary_search_term")
    def glossary_search_term_tool(term_src: str) -> str:
        """Search for a glossary term by source text.

        Returns:
            str: Glossary entry or not-found message.
        """
        return glossary_search_term(context, term_src)

    @tool("glossary_read_entry")
    def glossary_read_entry_tool(term_src: str) -> str:
        """Read a specific glossary entry if present.

        Returns:
            str: Glossary entry or not-found message.
        """
        return glossary_read_entry(context, term_src)

    @tool("contextdoc_list_all")
    async def contextdoc_list_all_tool() -> str:
        """List available context documents.

        Returns:
            str: Available docs listing.
        """
        return await contextdoc_list_all(context)

    @tool("contextdoc_read_doc")
    async def contextdoc_read_doc_tool(filename: str) -> str:
        """Read a specific context document.

        Returns:
            str: Document contents or not-found notice.
        """
        return await contextdoc_read_doc(context, filename)

    return [
        scene_read_overview_tool,
        scene_update_locations_tool,
        location_read_entry_tool,
        location_create_entry_tool,
        location_update_name_tgt_tool,
        location_update_description_tool,
        glossary_search_term_tool,
        glossary_read_entry_tool,
        contextdoc_list_all_tool,
        contextdoc_read_doc_tool,
    ]
