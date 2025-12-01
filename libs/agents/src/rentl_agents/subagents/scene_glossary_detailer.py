"""Scene glossary detailer subagent."""

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
from rentl_agents.tools.glossary import (
    glossary_create_entry,
    glossary_read_entry,
    glossary_search_term,
    glossary_update_entry,
)
from rentl_agents.tools.scene import scene_read_overview


class SceneGlossaryResult(BaseModel):
    """Result structure from scene glossary detailer subagent."""

    entries_added: int = Field(description="Number of glossary entries added from the scene.")
    entries_updated: int = Field(description="Number of glossary entries updated from the scene.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant extracting glossary-worthy terms from a scene.

Workflow:
1. Read the scene overview to see transcript and context.
2. Identify key terms that need consistent translation (honorifics, names, cultural items).
3. Use glossary_search_term and glossary_read_entry to check existing entries.
4. Add new entries with glossary_create_entry or refine with glossary_update_entry.
5. End the conversation when relevant glossary updates are recorded."""


async def detail_scene_glossary(
    context: ProjectContext,
    scene_id: str,
    *,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> SceneGlossaryResult:
    """Run the scene glossary detailer for *scene_id* and return counts.

    Returns:
        SceneGlossaryResult: Added/updated glossary counts.
    """
    logger.info("Detailing scene glossary %s", scene_id)
    initial_count = len(context.glossary)
    update_counter = context._glossary_update_count if hasattr(context, "_glossary_update_count") else 0
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_scene_glossary_detailer_subagent(context, checkpointer=effective_checkpointer)

    user_prompt = (
        f"Curate glossary terms found in scene {scene_id}. Use glossary_create_entry or glossary_update_entry."
    )
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'scene-glossary'}:{scene_id}",
    )

    final_count = len(context.glossary)
    entries_added = max(final_count - initial_count, 0)
    entries_updated = (
        max(context._glossary_update_count - update_counter, 0) if hasattr(context, "_glossary_update_count") else 0
    )
    return SceneGlossaryResult(entries_added=entries_added, entries_updated=entries_updated)


def create_scene_glossary_detailer_subagent(
    context: ProjectContext,
    *,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create scene glossary detailer LangChain subagent.

    Returns:
        CompiledStateGraph: Runnable agent graph.
    """
    tools = _build_scene_glossary_detailer_tools(context)
    model = get_default_chat_model()
    interrupt_on = {
        "glossary_create_entry": True,
        "glossary_update_entry": True,
    }
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )


def _build_scene_glossary_detailer_tools(context: ProjectContext) -> list[BaseTool]:
    """Return tools for the scene glossary detailer bound to the shared context."""

    @tool("scene_read_overview")
    async def scene_read_overview_tool(scene_id: str) -> str:
        """Read scene overview with transcript.

        Returns:
            str: Scene overview text.
        """
        return await scene_read_overview(context, scene_id)

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

    @tool("glossary_create_entry")
    async def glossary_create_entry_tool(term_src: str, term_tgt: str, notes: str | None = None) -> str:
        """Add a new glossary entry.

        Returns:
            str: Status message.
        """
        return await glossary_create_entry(context, term_src, term_tgt, notes)

    @tool("glossary_update_entry")
    async def glossary_update_entry_tool(term_src: str, term_tgt: str | None = None, notes: str | None = None) -> str:
        """Update an existing glossary entry.

        Returns:
            str: Status message.
        """
        return await glossary_update_entry(context, term_src, term_tgt, notes)

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
        glossary_search_term_tool,
        glossary_read_entry_tool,
        glossary_create_entry_tool,
        glossary_update_entry_tool,
        contextdoc_list_all_tool,
        contextdoc_read_doc_tool,
    ]
