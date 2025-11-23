"""Tools for route-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext


def build_route_tools(
    context: ProjectContext,
    route_id: str,
    *,
    allow_overwrite: bool = False,
) -> list:
    """Construct tools bound to a specific route.

    Returns:
        list: Tool callables ready to supply to ``create_deep_agent``.
    """
    route = context.get_route(route_id)

    @tool("read_route")
    def read_route() -> str:
        """Return current metadata for this route."""
        parts = [
            f"Route ID: {route.id}",
            f"Route Name: {route.name}",
            f"Scene IDs: {', '.join(route.scene_ids) if route.scene_ids else '(none)'}",
            f"Synopsis: {route.synopsis or '(not set)'}",
            f"Primary Characters: {', '.join(route.primary_characters) if route.primary_characters else '(not set)'}",
        ]
        return "\n".join(parts)

    @tool("list_context_docs")
    async def list_context_docs() -> str:
        """Return the available context document names."""
        docs = await context.list_context_docs()
        return "\n".join(docs) if docs else "(no context docs)"

    @tool("read_context_doc")
    async def read_context_doc(filename: str) -> str:
        """Return the contents of a context document."""
        return await context.read_context_doc(filename)

    has_updated_synopsis = False
    has_updated_characters = False

    @tool("update_route_synopsis")
    async def update_route_synopsis(synopsis: str) -> str:
        """Update the synopsis for this route.

        Args:
            synopsis: Concise narrative summary of the route (1-3 sentences).

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_updated_synopsis
        if has_updated_synopsis:
            return "Synopsis already updated. Provide a final assistant response."

        await context.update_route_synopsis(route_id, synopsis, allow_overwrite=allow_overwrite)
        has_updated_synopsis = True
        return "Synopsis updated."

    @tool("update_route_characters")
    async def update_route_characters(character_ids: list[str]) -> str:
        """Update the primary characters for this route.

        Args:
            character_ids: List of character IDs who are key to this route.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_updated_characters
        if has_updated_characters:
            return "Primary characters already updated. Provide a final assistant response."

        await context.update_route_characters(route_id, character_ids, allow_overwrite=allow_overwrite)
        has_updated_characters = True
        return "Primary characters updated."

    return [
        read_route,
        list_context_docs,
        read_context_doc,
        update_route_synopsis,
        update_route_characters,
    ]
