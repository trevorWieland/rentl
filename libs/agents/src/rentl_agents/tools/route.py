"""Shared route tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def route_read_entry(context: ProjectContext, route_id: str) -> str:
    """Return current metadata for this route.

    Returns:
        str: Route metadata string.
    """
    logger.info("Tool call: route_read_entry(route_id=%s)", route_id)
    route = context.get_route(route_id)
    parts = [
        f"Route ID: {route.id}",
        f"Route Name: {route.name}",
        f"Scene IDs: {', '.join(route.scene_ids) if route.scene_ids else '(none)'}",
        f"Synopsis: {route.synopsis or '(not set)'}",
        f"Primary Characters: {', '.join(route.primary_characters) if route.primary_characters else '(not set)'}",
    ]
    return "\n".join(parts)


async def route_create_entry(
    context: ProjectContext, route_id: str, name: str, scene_ids: list[str] | None = None
) -> str:
    """Create a new route entry with provenance tracking.

    Returns:
        str: Confirmation message after persistence or duplication notice.
    """
    from datetime import date

    logger.info("Tool call: route_create_entry(route_id=%s)", route_id)
    origin = f"agent:route_outline_builder:{date.today().isoformat()}"
    return await context.add_route(route_id, name, scene_ids or [], origin=origin)


async def route_update_synopsis(
    context: ProjectContext, route_id: str, synopsis: str, *, updated_synopsis: set[str]
) -> str:
    """Update the synopsis for this route.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if route_id in updated_synopsis:
        return "Synopsis already updated. Provide a final assistant response."

    logger.info("Tool call: route_update_synopsis(route_id=%s)", route_id)
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

    origin = f"agent:route_outline_builder:{date.today().isoformat()}"
    result = await context.update_route_synopsis(route_id, synopsis, origin)
    updated_synopsis.add(route_id)
    return result


async def route_update_primary_characters(
    context: ProjectContext, route_id: str, character_ids: list[str], *, updated_characters: set[str]
) -> str:
    """Update the primary characters for this route.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if route_id in updated_characters:
        return "Primary characters already updated. Provide a final assistant response."

    logger.info("Tool call: route_update_primary_characters(route_id=%s)", route_id)
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

    origin = f"agent:route_outline_builder:{date.today().isoformat()}"
    result = await context.update_route_characters(route_id, character_ids, origin)
    updated_characters.add(route_id)
    return result


async def route_delete_entry(context: ProjectContext, route_id: str) -> str:
    """Delete a route entry with HITL protection for human-authored fields.

    Returns:
        str: Status or approval message.
    """
    route = context.routes.get(route_id)
    if not route:
        return f"Route '{route_id}' not found."

    if any(
        origin == "human"
        for origin in (
            route.name_origin,
            route.synopsis_origin,
            route.primary_characters_origin,
        )
    ):
        return f"APPROVAL REQUIRED to delete route '{route_id}' with human-authored fields."

    logger.info("Tool call: route_delete_entry(route_id=%s)", route_id)
    return await context.delete_route(route_id)
