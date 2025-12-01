"""Glossary curator subagent.

This subagent proposes new glossary entries or updates to existing entries
with HITL approval for consistent terminology management.
"""

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
    glossary_delete_entry,
    glossary_merge_entries,
    glossary_read_entry,
    glossary_search_term,
    glossary_update_entry,
)


class GlossaryDetailResult(BaseModel):
    """Result structure from glossary curator subagent."""

    entries_added: int = Field(description="Number of new glossary entries added.")
    entries_updated: int = Field(description="Number of existing glossary entries updated.")
    total_entries: int = Field(description="Total number of glossary entries after curation.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant managing glossary entries.

Your task is to curate terminology for consistent translation.

**Workflow:**
1. Call `contextdoc_list_all()` to see available context documents
2. Call `contextdoc_read_doc(filename)` to review each document for terminology
    3. Call `glossary_search_term(term)` to check for existing entries
    4. Call `glossary_create_entry(term_src, term_tgt, notes)` for new important terms
    5. Call `glossary_update_entry(term_src, term_tgt, notes)` to refine existing entries
    6. Call `glossary_merge_entries(source_term, target_term)` to merge duplicates when needed
    7. End the conversation once curation is complete

**Important:**
- Focus on terms needing consistent translation (honorifics, character names, locations, cultural terms)
- Provide clear target language renderings and translator guidance in notes (notes should be in the source language)
- Be selective - not every word needs a glossary entry
- Respect existing human-authored data (you may be asked for approval before overwriting)
"""


def create_glossary_curator_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create glossary curator subagent for terminology management and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for glossary curation.
    """
    tools = _build_glossary_curator_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()

    interrupt_on = {
        "glossary_create_entry": True,
        "glossary_update_entry": True,
        "glossary_delete_entry": True,
        "glossary_merge_entries": True,
    }

    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )
    return graph


def build_glossary_curator_user_prompt(context: ProjectContext, *, current_entries: int) -> str:
    """Construct the user prompt for the glossary curator.

    Returns:
        str: User prompt content to send to the glossary curator agent.
    """
    source_lang = context.game.source_lang.upper()
    target_lang = context.game.target_lang.upper()
    return f"""Curate the glossary for this game project.

Source Language: {source_lang}
Target Language: {target_lang}
Current Glossary Entries: {current_entries}

Instructions:
1. Review context documents to understand key terminology
2. Search for existing glossary entries that may need refinement
3. Add new entries for important untranslated terms (honorifics, names, cultural terms) with term_tgt in {target_lang} and notes in {source_lang}
4. Update existing entries if they need better target translations or notes (keep notes in {source_lang})
5. End conversation when glossary curation is complete

Begin curation now."""


async def detail_glossary(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> GlossaryDetailResult:
    """Run the glossary curator agent and return curation results.

    Args:
        context: Project context with metadata.
        allow_overwrite: Allow overwriting existing human-authored metadata.
        decision_handler: Optional callback to resolve HITL interrupts.
        thread_id: Optional thread identifier for resumable runs.
        checkpointer: Optional LangGraph checkpointer (defaults to SQLite if configured).

    Returns:
        GlossaryDetailResult: Curation statistics.
    """
    logger.info("Curating glossary")
    initial_count = len(context.glossary)

    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_glossary_curator_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    user_prompt = build_glossary_curator_user_prompt(context, current_entries=initial_count)

    # Invoke the subagent directly (for flow usage)
    logger.debug("Glossary curator prompt:\n%s", user_prompt)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'glossary-curator'}",
    )

    # Calculate statistics
    final_count = len(context.glossary)
    entries_added = final_count - initial_count
    entries_updated = context._glossary_update_count

    result = GlossaryDetailResult(
        entries_added=entries_added,
        entries_updated=entries_updated,
        total_entries=final_count,
    )

    logger.info(
        "Glossary curation complete: %d added, %d updated, %d total",
        result.entries_added,
        result.entries_updated,
        result.total_entries,
    )

    return result


def _build_glossary_curator_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Return tools for the glossary curator subagent bound to the shared context."""
    context_doc_tools = _build_context_doc_tools(context)

    @tool("glossary_search_term")
    def search_glossary_tool(term_src: str) -> str:
        """Search for a glossary entry by source term.

        Returns:
            str: Glossary entry details or 'not found'.
        """
        return glossary_search_term(context, term_src)

    @tool("glossary_read_entry")
    def read_glossary_entry_tool(term_src: str) -> str:
        """Return a specific glossary entry if present."""
        return glossary_read_entry(context, term_src)

    @tool("glossary_create_entry")
    async def add_glossary_entry_tool(term_src: str, term_tgt: str, notes: str | None = None) -> str:
        """Add a new glossary entry.

        Returns:
            str: Confirmation message after persistence.
        """
        return await glossary_create_entry(context, term_src, term_tgt, notes)

    @tool("glossary_update_entry")
    async def update_glossary_entry_tool(term_src: str, term_tgt: str | None = None, notes: str | None = None) -> str:
        """Update an existing glossary entry.

        Returns:
            str: Confirmation message after persistence.
        """
        return await glossary_update_entry(context, term_src, term_tgt, notes)

    @tool("glossary_delete_entry")
    async def delete_glossary_entry_tool(term_src: str) -> str:
        """Delete a glossary entry if it exists.

        Returns:
            str: Status message indicating deletion or not-found.
        """
        return await glossary_delete_entry(context, term_src)

    @tool("glossary_merge_entries")
    async def glossary_merge_entries_tool(source_term: str, target_term: str) -> str:
        """Merge a source glossary entry into a target entry.

        Returns:
            str: Status or approval message.
        """
        return await glossary_merge_entries(context, source_term, target_term)

    return [
        search_glossary_tool,
        read_glossary_entry_tool,
        *context_doc_tools,
        add_glossary_entry_tool,
        update_glossary_entry_tool,
        delete_glossary_entry_tool,
        glossary_merge_entries_tool,
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
