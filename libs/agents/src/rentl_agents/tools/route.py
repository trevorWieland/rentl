"""Tools for route-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.context_docs import build_context_doc_tools
from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def build_route_tools(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
) -> list:
    """Construct tools usable across routes.

    Returns:
        list: Tool callables ready to supply to ``create_agent``.
    """
    updated_synopsis: set[str] = set()
    updated_characters: set[str] = set()
    context_doc_tools = build_context_doc_tools(context)

    @tool("read_route")
    def read_route(route_id: str) -> str:
        """Return current metadata for this route."""
        logger.info("Tool call: read_route(route_id=%s)", route_id)
        route = context.get_route(route_id)
        parts = [
            f"Route ID: {route.id}",
            f"Route Name: {route.name}",
            f"Scene IDs: {', '.join(route.scene_ids) if route.scene_ids else '(none)'}",
            f"Synopsis: {route.synopsis or '(not set)'}",
            f"Primary Characters: {', '.join(route.primary_characters) if route.primary_characters else '(not set)'}",
        ]
        return "\n".join(parts)

    @tool("update_route_synopsis")
    async def update_route_synopsis(route_id: str, synopsis: str) -> str:
        """Update the synopsis for this route.

        Args:
            route_id: Route identifier.
            synopsis: Concise narrative summary of the route (1-3 sentences).

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        if route_id in updated_synopsis:
            return "Synopsis already updated. Provide a final assistant response."

        logger.info("Tool call: update_route_synopsis(route_id=%s)", route_id)
        route = context.get_route(route_id)
        approval = request_if_human_authored(
            operation="update",
            target=f"route.{route_id}.synopsis",
            current_value=route.synopsis,
            current_origin=route.synopsis_origin,
            proposed_value=synopsis,
        )
        if approval:
            return approval

        origin = f"agent:route_detailer:{date.today().isoformat()}"
        result = await context.update_route_synopsis(route_id, synopsis, origin)
        updated_synopsis.add(route_id)
        return result

    @tool("update_route_characters")
    async def update_route_characters(route_id: str, character_ids: list[str]) -> str:
        """Update the primary characters for this route.

        Args:
            route_id: Route identifier.
            character_ids: List of character IDs who are key to this route.

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        if route_id in updated_characters:
            return "Primary characters already updated. Provide a final assistant response."

        logger.info("Tool call: update_route_characters(route_id=%s)", route_id)
        route = context.get_route(route_id)
        approval = request_if_human_authored(
            operation="update",
            target=f"route.{route_id}.primary_characters",
            current_value=route.primary_characters,
            current_origin=route.primary_characters_origin,
            proposed_value=character_ids,
        )
        if approval:
            return approval

        origin = f"agent:route_detailer:{date.today().isoformat()}"
        result = await context.update_route_characters(route_id, character_ids, origin)
        updated_characters.add(route_id)
        return result

    return [
        read_route,
        *context_doc_tools,
        update_route_synopsis,
        update_route_characters,
    ]
