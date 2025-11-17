"""Tools for scene-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext
from rentl_core.model.line import SourceLine


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
    summary_prefix = "Existing summary present." if scene.annotations.summary else "Summary not yet recorded."

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

    has_written = False

    @tool("write_scene_summary")
    async def write_scene_summary(summary: str) -> str:
        """Store the final summary for this scene.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_written
        if has_written:
            return "Summary already stored. Provide a final assistant response."

        await context.set_scene_summary(scene_id, summary, allow_overwrite=allow_overwrite)
        has_written = True
        return "Summary stored."

    return [read_scene_overview, list_context_docs, read_context_doc, write_scene_summary]
