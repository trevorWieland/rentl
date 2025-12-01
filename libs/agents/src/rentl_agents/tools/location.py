"""Shared location tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def location_read_entry(context: ProjectContext, location_id: str) -> str:
    """Return current metadata for this location.

    Returns:
        str: Location metadata string.
    """
    logger.info("Tool call: location_read_entry(location_id=%s)", location_id)
    location = context.get_location(location_id)
    parts = [
        f"Location ID: {location.id}",
        f"Source Name: {location.name_src}",
        f"Target Name: {location.name_tgt or '(not set)'}",
        f"Description: {location.description or '(not set)'}",
    ]
    return "\n".join(parts)


async def location_create_entry(
    context: ProjectContext,
    location_id: str,
    name_src: str,
    name_tgt: str | None = None,
    description: str | None = None,
) -> str:
    """Add a new location entry with provenance tracking.

    Returns:
        str: Status message after attempting creation.
    """
    from datetime import date

    logger.info("Tool call: location_create_entry(location_id=%s)", location_id)
    origin = f"agent:location_detailer:{date.today().isoformat()}"
    return await context.add_location(
        location_id,
        name_src,
        name_tgt=name_tgt,
        description=description,
        origin=origin,
    )


async def location_update_name_tgt(
    context: ProjectContext, location_id: str, name_tgt: str, *, updated_name_tgt: set[str]
) -> str:
    """Update the target language name for this location.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if location_id in updated_name_tgt:
        return "Target name already updated. Provide a final assistant response."

    logger.info("Tool call: location_update_name_tgt(location_id=%s)", location_id)
    location = context.get_location(location_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"location.{location_id}.name_tgt",
        current_value=location.name_tgt,
        current_origin=location.name_tgt_origin,
        proposed_value=name_tgt,
    )
    if approval:
        return approval

    origin = f"agent:location_detailer:{date.today().isoformat()}"
    result = await context.update_location_name_tgt(location_id, name_tgt, origin)
    updated_name_tgt.add(location_id)
    return result


async def location_update_description(
    context: ProjectContext, location_id: str, description: str, *, updated_description: set[str]
) -> str:
    """Update the description for this location.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if location_id in updated_description:
        return "Description already updated. Provide a final assistant response."

    logger.info("Tool call: location_update_description(location_id=%s)", location_id)
    location = context.get_location(location_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"location.{location_id}.description",
        current_value=location.description,
        current_origin=location.description_origin,
        proposed_value=description,
    )
    if approval:
        return approval

    origin = f"agent:location_detailer:{date.today().isoformat()}"
    result = await context.update_location_description(location_id, description, origin)
    updated_description.add(location_id)
    return result
