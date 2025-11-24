"""Tools for scene-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger


def build_scene_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list:
    """Construct scene tools usable across scenes.

    Returns:
        list: Tool callables ready to supply to ``create_agent``.
    """
    written_summary: set[str] = set()
    written_tags: set[str] = set()
    written_characters: set[str] = set()
    written_locations: set[str] = set()

    @tool("read_scene_overview")
    async def read_scene_overview(scene_id: str) -> str:
        """Return metadata and transcript for the scene."""
        lines = await context.load_scene_lines(scene_id)
        scene = context.get_scene(scene_id)

        formatted_rows: list[str] = []
        for idx, line in enumerate(lines, start=1):
            speaker = line.meta.speaker or "Narration"
            prefix = "[CHOICE] " if line.is_choice else ""
            notes = f" (notes: {'; '.join(line.meta.style_notes)})" if line.meta.style_notes else ""
            formatted_rows.append(f"{idx}. {prefix}{speaker}: {line.text}{notes}")
        transcript = "\n".join(formatted_rows)

        if scene.annotations.summary and not allow_overwrite:
            summary_text = scene.annotations.summary
            summary_prefix = "Existing summary:"
        elif scene.annotations.summary and allow_overwrite:
            summary_prefix = "Existing summary will be replaced (content hidden)."
            summary_text = None
        else:
            summary_prefix = "Summary not yet recorded."
            summary_text = None

        meta = [
            f"Title: {scene.title}",
            f"Routes: {', '.join(scene.route_ids)}",
            f"Tags: {', '.join(scene.annotations.tags)}",
            f"Primary Characters: {', '.join(scene.annotations.primary_characters)}",
            f"Locations: {', '.join(scene.annotations.locations)}",
            summary_prefix,
            "Transcript:",
            transcript,
        ]
        if summary_text:
            meta.extend(["Current summary:", summary_text])
        return "\n".join(meta)

    @tool("list_context_docs")
    async def list_context_docs() -> str:
        """Return the available context document names."""
        docs = await context.list_context_docs()
        return "\n".join(docs) if docs else "(no context docs)"

    @tool("read_context_doc")
    async def read_context_doc(filename: str) -> str:
        """Return the contents of a context document."""
        return await context.read_context_doc(filename)

    @tool("write_scene_summary")
    async def write_scene_summary(scene_id: str, summary: str) -> str:
        """Store the final summary for this scene.

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        if scene_id in written_summary:
            return "Summary already stored. Provide a final assistant response."

        origin = f"agent:scene_detailer:{date.today().isoformat()}"
        result = await context.set_scene_summary(scene_id, summary, origin)
        written_summary.add(scene_id)
        return result

    @tool("write_scene_tags")
    async def write_scene_tags(scene_id: str, tags: list[str]) -> str:
        """Store tags for this scene.

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        if scene_id in written_tags:
            return "Tags already stored. Provide a final assistant response."

        origin = f"agent:scene_detailer:{date.today().isoformat()}"
        result = await context.set_scene_tags(scene_id, tags, origin)
        written_tags.add(scene_id)
        return result

    @tool("write_primary_characters")
    async def write_primary_characters(scene_id: str, character_ids: list[str]) -> str:
        """Store primary characters identified in this scene.

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        if scene_id in written_characters:
            return "Characters already stored. Provide a final assistant response."

        origin = f"agent:scene_detailer:{date.today().isoformat()}"
        result = await context.set_scene_characters(scene_id, character_ids, origin)
        written_characters.add(scene_id)
        return result

    @tool("write_scene_locations")
    async def write_scene_locations(scene_id: str, location_ids: list[str]) -> str:
        """Store locations identified in this scene.

        Returns:
            str: Confirmation message after persistence.
        """
        from datetime import date

        if scene_id in written_locations:
            return "Locations already stored. Provide a final assistant response."

        origin = f"agent:scene_detailer:{date.today().isoformat()}"
        result = await context.set_scene_locations(scene_id, location_ids, origin)
        written_locations.add(scene_id)
        return result

    return [
        read_scene_overview,
        list_context_docs,
        read_context_doc,
        write_scene_summary,
        write_scene_tags,
        write_primary_characters,
        write_scene_locations,
    ]


logger = get_logger(__name__)
