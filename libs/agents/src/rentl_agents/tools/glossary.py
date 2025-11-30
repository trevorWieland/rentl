"""Tools for glossary-aware agents."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.context_docs import build_context_doc_tools
from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def search_glossary(context: ProjectContext, term_src: str) -> str:
    """Search for a glossary entry by source term.

    Returns:
        str: Glossary entry details or "not found" message.
    """
    logger.info("Tool call: search_glossary(term_src=%s)", term_src)
    for entry in context.glossary:
        if entry.term_src == term_src:
            parts = [
                f"Term (source): {entry.term_src}",
                f"Term (target): {entry.term_tgt or '(not set)'}",
                f"Notes: {entry.notes or '(not set)'}",
            ]
            return "\n".join(parts)
    return f"No glossary entry found for '{term_src}'"


def read_glossary_entry(context: ProjectContext, term_src: str) -> str:
    """Return a specific glossary entry if present."""
    logger.info("Tool call: read_glossary_entry(term_src=%s)", term_src)
    for entry in context.glossary:
        if entry.term_src == term_src:
            parts = [
                f"Term (source): {entry.term_src}",
                f"Term (target): {entry.term_tgt or '(not set)'}",
                f"Notes: {entry.notes or '(not set)'}",
            ]
            return "\n".join(parts)
    return f"No glossary entry found for '{term_src}'"


async def add_glossary_entry(context: ProjectContext, term_src: str, term_tgt: str, notes: str | None = None) -> str:
    """Add a new glossary entry.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    logger.info("Tool call: add_glossary_entry(term_src=%s)", term_src)
    origin = f"agent:glossary_curator:{date.today().isoformat()}"
    result = await context.add_glossary_entry(term_src=term_src, term_tgt=term_tgt, notes=notes, origin=origin)
    return result


async def update_glossary_entry(
    context: ProjectContext, term_src: str, term_tgt: str | None = None, notes: str | None = None
) -> str:
    """Update an existing glossary entry.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    logger.info("Tool call: update_glossary_entry(term_src=%s)", term_src)
    existing_entry = next((entry for entry in context.glossary if entry.term_src == term_src), None)
    if existing_entry:
        if term_tgt is not None:
            approval = request_if_human_authored(
                operation="update",
                target=f"glossary.{term_src}.term_tgt",
                current_value=existing_entry.term_tgt,
                current_origin=existing_entry.term_tgt_origin,
                proposed_value=term_tgt,
            )
            if approval:
                return approval
        if notes is not None:
            approval = request_if_human_authored(
                operation="update",
                target=f"glossary.{term_src}.notes",
                current_value=existing_entry.notes,
                current_origin=existing_entry.notes_origin,
                proposed_value=notes,
            )
            if approval:
                return approval

    origin = f"agent:glossary_curator:{date.today().isoformat()}"
    result = await context.update_glossary_entry(term_src=term_src, term_tgt=term_tgt, notes=notes, origin=origin)
    return result


async def delete_glossary_entry(context: ProjectContext, term_src: str) -> str:
    """Delete a glossary entry if it exists.

    Returns:
        str: Status message indicating deletion or not-found.
    """
    logger.info("Tool call: delete_glossary_entry(term_src=%s)", term_src)
    return await context.delete_glossary_entry(term_src)


def build_glossary_tools(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
) -> list[BaseTool]:
    """Construct tools for glossary curation.

    Returns:
        list[BaseTool]: Tool callables ready to supply to ``create_deep_agent``.
    """
    context_doc_tools = build_context_doc_tools(context)

    @tool("search_glossary")
    def search_glossary_tool(term_src: str) -> str:
        """Search for a glossary entry by source term.

        Returns:
            str: Glossary entry details or "not found" message.
        """
        return search_glossary(context, term_src)

    @tool("read_glossary_entry")
    def read_glossary_entry_tool(term_src: str) -> str:
        """Return a specific glossary entry if present."""
        return read_glossary_entry(context, term_src)

    @tool("add_glossary_entry")
    async def add_glossary_entry_tool(term_src: str, term_tgt: str, notes: str | None = None) -> str:
        """Add a new glossary entry.

        Returns:
            str: Confirmation message after persistence.
        """
        return await add_glossary_entry(context, term_src, term_tgt, notes)

    @tool("update_glossary_entry")
    async def update_glossary_entry_tool(term_src: str, term_tgt: str | None = None, notes: str | None = None) -> str:
        """Update an existing glossary entry.

        Returns:
            str: Confirmation message after persistence.
        """
        return await update_glossary_entry(context, term_src, term_tgt, notes)

    @tool("delete_glossary_entry")
    async def delete_glossary_entry_tool(term_src: str) -> str:
        """Delete a glossary entry if it exists.

        Returns:
            str: Status message indicating deletion or not-found.
        """
        return await delete_glossary_entry(context, term_src)

    return [
        search_glossary_tool,
        read_glossary_entry_tool,
        *context_doc_tools,
        add_glossary_entry_tool,
        update_glossary_entry_tool,
        delete_glossary_entry_tool,
    ]
