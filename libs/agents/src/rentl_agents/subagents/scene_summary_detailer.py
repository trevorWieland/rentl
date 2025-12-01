"""Scene summary detailer subagent."""

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
from rentl_agents.tools.scene import scene_read_overview, scene_read_redacted, scene_update_summary


class SceneSummaryResult(BaseModel):
    """Result structure from scene summary detailer subagent."""

    summary: str = Field(description="Concise 1-2 sentence scene summary in source language.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant writing a concise summary for a scene.

Workflow:
1. Read the scene overview to understand context and transcript.
2. If overwriting is allowed, use the redacted overview; otherwise use the normal overview.
3. Write a 1-2 sentence summary in the source language capturing mood, key events, and outcomes.
4. Call scene_update_summary once with your final summary.
5. End the conversation when the summary is recorded."""


async def detail_scene_summary(
    context: ProjectContext,
    scene_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> SceneSummaryResult:
    """Run the scene summary detailer for *scene_id* and return the summary.

    Returns:
        SceneSummaryResult: Scene summary payload.
    """
    logger.info("Detailing scene summary %s", scene_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_scene_summary_detailer_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    user_prompt = build_scene_summary_user_prompt(context, scene_id)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'scene-summary'}:{scene_id}",
    )

    updated_scene = context.get_scene(scene_id)
    return SceneSummaryResult(summary=updated_scene.annotations.summary or "")


def create_scene_summary_detailer_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create scene summary detailer LangChain subagent.

    Returns:
        CompiledStateGraph: Runnable agent graph.
    """
    tools = _build_scene_summary_detailer_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    interrupt_on = {
        "scene_update_summary": True,
    }
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )


def build_scene_summary_user_prompt(context: ProjectContext, scene_id: str) -> str:
    """Construct the user prompt for the scene summary detailer.

    Returns:
        str: User prompt text.
    """
    source_lang = context.game.source_lang.upper()
    return f"Write a concise summary for scene {scene_id} in {source_lang}. Use scene_update_summary once with your final summary."


def _build_scene_summary_detailer_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Return tools for the scene summary detailer bound to the shared context."""
    written_summary: set[str] = set()

    @tool("scene_read_overview")
    async def scene_read_overview_tool(scene_id: str) -> str:
        """Read scene overview with transcript and existing summary if present.

        Returns:
            str: Scene overview text.
        """
        if allow_overwrite:
            return await scene_read_redacted(context, scene_id)
        return await scene_read_overview(context, scene_id)

    @tool("scene_update_summary")
    async def scene_update_summary_tool(scene_id: str, summary: str) -> str:
        """Store the final summary for this scene.

        Returns:
            str: Status or approval message.
        """
        return await scene_update_summary(context, scene_id, summary, written_summary=written_summary)

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
        scene_update_summary_tool,
        character_read_entry_tool,
        location_read_entry_tool,
        glossary_search_term_tool,
        glossary_read_entry_tool,
        contextdoc_list_all_tool,
        contextdoc_read_doc_tool,
    ]
