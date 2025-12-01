"""Scene tag detailer subagent."""

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
from rentl_agents.tools.character import character_read_entry
from rentl_agents.tools.context_docs import contextdoc_list_all, contextdoc_read_doc
from rentl_agents.tools.glossary import glossary_read_entry, glossary_search_term
from rentl_agents.tools.location import location_read_entry
from rentl_agents.tools.scene import scene_read_overview, scene_update_tags


class SceneTagResult(BaseModel):
    """Result structure from scene tag detailer subagent."""

    tags: list[str] = Field(description="Descriptive tags for the scene.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant assigning tags to a scene.

Workflow:
1. Read the scene overview to understand context and transcript.
2. Propose 3-6 concise tags in the source language capturing tone, setting, and events.
3. Call scene_update_tags once with your final tag list.
4. End the conversation when tags are recorded."""


async def detail_scene_tags(
    context: ProjectContext,
    scene_id: str,
    *,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> SceneTagResult:
    """Run the scene tag detailer for *scene_id* and return tags.

    Returns:
        SceneTagResult: Scene tags payload.
    """
    logger.info("Detailing scene tags %s", scene_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_scene_tag_detailer_subagent(context, checkpointer=effective_checkpointer)

    user_prompt = f"Assign concise tags for scene {scene_id}. Use scene_update_tags once."
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'scene-tags'}:{scene_id}",
    )

    updated_scene = context.get_scene(scene_id)
    return SceneTagResult(tags=updated_scene.annotations.tags)


def create_scene_tag_detailer_subagent(
    context: ProjectContext,
    *,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create scene tag detailer LangChain subagent.

    Returns:
        CompiledStateGraph: Runnable agent graph.
    """
    tools = _build_scene_tag_detailer_tools(context)
    model = get_default_chat_model()
    interrupt_on = {"scene_update_tags": True}
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )


def _build_scene_tag_detailer_tools(context: ProjectContext) -> list[BaseTool]:
    """Return tools for the scene tag detailer bound to the shared context."""
    written_tags: set[str] = set()

    @tool("scene_read_overview")
    async def scene_read_overview_tool(scene_id: str) -> str:
        """Read scene overview with transcript.

        Returns:
            str: Scene overview text.
        """
        return await scene_read_overview(context, scene_id)

    @tool("scene_update_tags")
    async def scene_update_tags_tool(scene_id: str, tags: list[str]) -> str:
        """Store tags for this scene.

        Returns:
            str: Status or approval message.
        """
        return await scene_update_tags(context, scene_id, tags, written_tags=written_tags)

    @tool("character_read_entry")
    def character_read_entry_tool(character_id: str) -> str:
        """Read character metadata.

        Returns:
            str: Character metadata string.
        """
        return character_read_entry(context, character_id)

    @tool("location_read_entry")
    def location_read_entry_tool(location_id: str) -> str:
        """Read location metadata.

        Returns:
            str: Location metadata string.
        """
        return location_read_entry(context, location_id)

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
        scene_update_tags_tool,
        character_read_entry_tool,
        location_read_entry_tool,
        glossary_search_term_tool,
        glossary_read_entry_tool,
        contextdoc_list_all_tool,
        contextdoc_read_doc_tool,
    ]
