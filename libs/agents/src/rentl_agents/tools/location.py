"""Tools for location-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext


def build_location_tools(
    context: ProjectContext,
    location_id: str,
    *,
    allow_overwrite: bool = False,
) -> list:
    """Construct tools bound to a specific location.

    Returns:
        list: Tool callables ready to supply to ``create_deep_agent``.
    """
    location = context.get_location(location_id)

    @tool("read_location")
    def read_location() -> str:
        """Return current metadata for this location."""
        parts = [
            f"Location ID: {location.id}",
            f"Source Name: {location.name_src}",
            f"Target Name: {location.name_tgt or '(not set)'}",
            f"Description: {location.description or '(not set)'}",
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

    has_updated_name_tgt = False
    has_updated_description = False

    @tool("update_location_name_tgt")
    async def update_location_name_tgt(name_tgt: str) -> str:
        """Update the target language name for this location.

        Args:
            name_tgt: Localized name in the target language.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_updated_name_tgt
        if has_updated_name_tgt:
            return "Target name already updated. Provide a final assistant response."

        await context.update_location_name_tgt(location_id, name_tgt, allow_overwrite=allow_overwrite)
        has_updated_name_tgt = True
        return "Target name updated."

    @tool("update_location_description")
    async def update_location_description(description: str) -> str:
        """Update the description for this location.

        Args:
            description: Location description with mood, atmosphere, and sensory details.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_updated_description
        if has_updated_description:
            return "Description already updated. Provide a final assistant response."

        await context.update_location_description(location_id, description, allow_overwrite=allow_overwrite)
        has_updated_description = True
        return "Description updated."

    return [
        read_location,
        list_context_docs,
        read_context_doc,
        update_location_name_tgt,
        update_location_description,
    ]
