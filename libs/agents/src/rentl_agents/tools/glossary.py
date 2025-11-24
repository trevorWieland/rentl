"""Tools for glossary-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def build_glossary_tools(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
) -> list:
    """Construct tools for glossary curation.

    Returns:
        list: Tool callables ready to supply to ``create_deep_agent``.
    """

    @tool("search_glossary")
    def search_glossary(term_src: str) -> str:
        """Search for a glossary entry by source term.

        Args:
            term_src: Source language term to search for.

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

    @tool("list_context_docs")
    async def list_context_docs() -> str:
        """Return the available context document names."""
        docs = await context.list_context_docs()
        return "\n".join(docs) if docs else "(no context docs)"

    @tool("read_context_doc")
    async def read_context_doc(filename: str) -> str:
        """Return the contents of a context document."""
        return await context.read_context_doc(filename)

    @tool("add_glossary_entry")
    async def add_glossary_entry(term_src: str, term_tgt: str, notes: str | None = None) -> str:
        """Add a new glossary entry.

        Args:
            term_src: Source language term.
            term_tgt: Target language rendering.
            notes: Optional translation guidance or context.

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        logger.info("Tool call: add_glossary_entry(term_src=%s)", term_src)
        origin = f"agent:glossary_curator:{date.today().isoformat()}"
        result = await context.add_glossary_entry(term_src=term_src, term_tgt=term_tgt, notes=notes, origin=origin)
        return result

    @tool("update_glossary_entry")
    async def update_glossary_entry(term_src: str, term_tgt: str | None = None, notes: str | None = None) -> str:
        """Update an existing glossary entry.

        Args:
            term_src: Source language term to update.
            term_tgt: New target language rendering (optional, keeps existing if not provided).
            notes: New translation notes (optional, keeps existing if not provided).

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

    return [
        search_glossary,
        list_context_docs,
        read_context_doc,
        add_glossary_entry,
        update_glossary_entry,
    ]
