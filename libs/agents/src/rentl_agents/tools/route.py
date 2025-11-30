"""Shared route tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def read_route(context: ProjectContext, route_id: str) -> str:
    """Return current metadata for this route.

    Returns:
        str: Route metadata string.
    """
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


async def update_route_synopsis(
    context: ProjectContext, route_id: str, synopsis: str, *, updated_synopsis: set[str]
) -> str:
    """Update the synopsis for this route.

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
        if approval.startswith("No change"):
            updated_synopsis.add(route_id)
        return approval

    origin = f"agent:route_detailer:{date.today().isoformat()}"
    result = await context.update_route_synopsis(route_id, synopsis, origin)
    updated_synopsis.add(route_id)
    return result


async def update_route_characters(
    context: ProjectContext, route_id: str, character_ids: list[str], *, updated_characters: set[str]
) -> str:
    """Update the primary characters for this route.

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
        if approval.startswith("No change"):
            updated_characters.add(route_id)
        return approval

    origin = f"agent:route_detailer:{date.today().isoformat()}"
    result = await context.update_route_characters(route_id, character_ids, origin)
    updated_characters.add(route_id)
    return result
