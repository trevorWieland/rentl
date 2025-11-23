"""Tools for scene-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext
from rentl_core.model.line import SourceLine
from rentl_core.util.logging import get_logger


def format_scene_lines(lines: list[SourceLine]) -> str:
    """Return a human-readable transcript for the scene."""
    formatted_rows: list[str] = []
    for idx, line in enumerate(lines, start=1):
        speaker = line.meta.speaker or "Narration"
        prefix = "[CHOICE] " if line.is_choice else ""
        notes = f" (notes: {'; '.join(line.meta.style_notes)})" if line.meta.style_notes else ""
        formatted_rows.append(f"{idx}. {prefix}{speaker}: {line.text}{notes}")
    return "\n".join(formatted_rows)


def build_scene_tools(
    context: ProjectContext,
    scene_id: str,
    lines: list[SourceLine],
    *,
    allow_overwrite: bool = False,
) -> list:
    """Construct tools bound to a specific scene.

    Returns:
        list: Tool callables ready to supply to ``create_deep_agent``.
    """
    transcript = format_scene_lines(lines)
    scene = context.get_scene(scene_id)
    if scene.annotations.summary and not allow_overwrite:
        summary_text = scene.annotations.summary
        summary_prefix = "Existing summary:"
    elif scene.annotations.summary and allow_overwrite:
        summary_prefix = "Existing summary will be replaced (content hidden)."
        summary_text = None
    else:
        summary_prefix = "Summary not yet recorded."
        summary_text = None

    @tool("read_scene_overview")
    def read_scene_overview() -> str:
        """Return metadata and transcript for the scene."""
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

    has_written_summary = False
    has_written_tags = False
    has_written_characters = False
    has_written_locations = False

    @tool("write_scene_summary")
    async def write_scene_summary(summary: str) -> str:
        """Store the final summary for this scene.

        Args:
            summary: Concise 1-2 sentence scene summary.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_written_summary
        if has_written_summary:
            return "Summary already stored. Provide a final assistant response."

        await context.set_scene_summary(scene_id, summary, allow_overwrite=allow_overwrite)
        has_written_summary = True
        return "Summary stored."

    @tool("write_scene_tags")
    async def write_scene_tags(tags: list[str]) -> str:
        """Store tags for this scene.

        Args:
            tags: List of quick descriptive tags (e.g., ["intro", "school", "conflict"]).

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_written_tags
        if has_written_tags:
            return "Tags already stored. Provide a final assistant response."

        await context.set_scene_tags(scene_id, tags, allow_overwrite=allow_overwrite)
        has_written_tags = True
        return f"Stored {len(tags)} tags."

    @tool("write_primary_characters")
    async def write_primary_characters(character_ids: list[str]) -> str:
        """Store primary characters identified in this scene.

        Args:
            character_ids: List of character IDs featured in the scene.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_written_characters
        if has_written_characters:
            return "Characters already stored. Provide a final assistant response."

        await context.set_scene_characters(scene_id, character_ids, allow_overwrite=allow_overwrite)
        has_written_characters = True
        return f"Stored {len(character_ids)} characters."

    @tool("write_scene_locations")
    async def write_scene_locations(location_ids: list[str]) -> str:
        """Store locations identified in this scene.

        Args:
            location_ids: List of location IDs where the scene takes place.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_written_locations
        if has_written_locations:
            return "Locations already stored. Provide a final assistant response."

        await context.set_scene_locations(scene_id, location_ids, allow_overwrite=allow_overwrite)
        has_written_locations = True
        return f"Stored {len(location_ids)} locations."

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
