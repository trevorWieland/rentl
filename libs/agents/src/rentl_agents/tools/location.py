"""Tools for location-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.context_docs import build_context_doc_tools
from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def build_location_tools(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
) -> list:
    """Construct tools usable across locations.

    Returns:
        list: Tool callables ready to supply to ``create_agent``.
    """
    updated_name_tgt: set[str] = set()
    updated_description: set[str] = set()
    context_doc_tools = build_context_doc_tools(context)

    @tool("read_location")
    def read_location(location_id: str) -> str:
        """Return current metadata for this location."""
        logger.info("Tool call: read_location(location_id=%s)", location_id)
        location = context.get_location(location_id)
        parts = [
            f"Location ID: {location.id}",
            f"Source Name: {location.name_src}",
            f"Target Name: {location.name_tgt or '(not set)'}",
            f"Description: {location.description or '(not set)'}",
        ]
        return "\n".join(parts)

    @tool("add_location")
    async def add_location(
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

        logger.info("Tool call: add_location(location_id=%s)", location_id)
        origin = f"agent:location_detailer:{date.today().isoformat()}"
        return await context.add_location(
            location_id,
            name_src,
            name_tgt=name_tgt,
            description=description,
            origin=origin,
        )

    @tool("update_location_name_tgt")
    async def update_location_name_tgt(location_id: str, name_tgt: str) -> str:
        """Update the target language name for this location.

        Args:
            location_id: Location identifier.
            name_tgt: Localized name in the target language.

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        if location_id in updated_name_tgt:
            return "Target name already updated. Provide a final assistant response."

        logger.info("Tool call: update_location_name_tgt(location_id=%s)", location_id)
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

    @tool("update_location_description")
    async def update_location_description(location_id: str, description: str) -> str:
        """Update the description for this location.

        Args:
            location_id: Location identifier.
            description: Location description with mood, atmosphere, and sensory details.

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        if location_id in updated_description:
            return "Description already updated. Provide a final assistant response."

        logger.info("Tool call: update_location_description(location_id=%s)", location_id)
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

    return [
        read_location,
        add_location,
        *context_doc_tools,
        update_location_name_tgt,
        update_location_description,
    ]
