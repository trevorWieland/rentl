"""Tools for glossary-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext


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
        # Check if entry already exists
        for entry in context.glossary:
            if entry.term_src == term_src:
                return f"Entry for '{term_src}' already exists. Use update_glossary_entry to modify it."

        await context.add_glossary_entry(
            term_src=term_src, term_tgt=term_tgt, notes=notes, allow_overwrite=allow_overwrite
        )
        return f"Added glossary entry for '{term_src}'."

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
        # Check if entry exists
        found = False
        for entry in context.glossary:
            if entry.term_src == term_src:
                found = True
                break

        if not found:
            return f"No entry found for '{term_src}'. Use add_glossary_entry to create it."

        await context.update_glossary_entry(
            term_src=term_src, term_tgt=term_tgt, notes=notes, allow_overwrite=allow_overwrite
        )
        return f"Updated glossary entry for '{term_src}'."

    return [
        search_glossary,
        list_context_docs,
        read_context_doc,
        add_glossary_entry,
        update_glossary_entry,
    ]
