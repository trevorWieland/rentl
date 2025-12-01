"""Context document tools (list/read) shared across agents."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


async def contextdoc_list_all(context: ProjectContext) -> str:
    """Return the available context document names."""
    docs = await context.list_context_docs()
    return "\n".join(docs) if docs else "(no context docs)"


async def contextdoc_read_doc(context: ProjectContext, filename: str) -> str:
    """Return the contents of a context document."""
    try:
        return await context.read_context_doc(filename)
    except FileNotFoundError:
        available = await context.list_context_docs()
        available_display = ", ".join(available) if available else "(none)"
        return f"Context doc not found: {filename}. Available: {available_display}."
