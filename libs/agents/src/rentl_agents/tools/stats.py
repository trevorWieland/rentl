"""Progress and completion tools for top-level agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext


def _get_completion_ratio(completed: int, total: int) -> float:
    """Return completion ratio with zero guard."""
    return round(completed / total, 3) if total else 0.0


def build_stats_tools(context: ProjectContext) -> list:
    """Return stats/progress tools bound to a specific project context.

    These tools are intended for top-level DeepAgents where the LLM should not
    be asked to pass the context explicitly.
    """

    @tool("get_context_status")
    def get_context_status() -> str:
        """Summarize context completion across scenes, characters, locations, and routes.

        Returns:
            str: Completion summary suitable for quick progress checks.
        """
        scenes = len(context.scenes)
        characters = len(context.characters)
        locations = len(context.locations)
        routes = len(context.routes)

        summaries = sum(1 for s in context.scenes.values() if s.annotations.summary)
        tags = sum(1 for s in context.scenes.values() if s.annotations.tags)
        primary_chars = sum(1 for s in context.scenes.values() if s.annotations.primary_characters)
        locs = sum(1 for s in context.scenes.values() if s.annotations.locations)

        return (
            "Context status:\n"
            f"- Scenes: {scenes} total | summaries {summaries}/{scenes} ({_get_completion_ratio(summaries, scenes)}) | "
            f"tags {tags}/{scenes} ({_get_completion_ratio(tags, scenes)}) | "
            f"primary_characters {primary_chars}/{scenes} ({_get_completion_ratio(primary_chars, scenes)}) | "
            f"locations {locs}/{scenes} ({_get_completion_ratio(locs, scenes)})\n"
            f"- Characters: {characters} total\n"
            f"- Locations: {locations} total\n"
            f"- Routes: {routes} total\n"
        )

    @tool("get_scene_completion")
    def get_scene_completion(scene_id: str) -> str:
        """Return detailed completion for a specific scene.

        Args:
            scene_id: Scene identifier.

        Returns:
            str: Human-readable scene completion status.
        """
        scene = context.get_scene(scene_id)
        annotations = scene.annotations
        parts = [
            f"Scene {scene_id}:",
            f"- Summary: {'yes' if annotations.summary else 'no'}",
            f"- Tags: {'yes' if annotations.tags else 'no'}",
            f"- Primary Characters: {'yes' if annotations.primary_characters else 'no'}",
            f"- Locations: {'yes' if annotations.locations else 'no'}",
        ]
        return "\n".join(parts)

    @tool("get_translation_progress")
    async def get_translation_progress(scene_id: str) -> str:
        """Report translation progress for a scene.

        Args:
            scene_id: Scene identifier.

        Returns:
            str: Translation progress summary.
        """
        await context._load_translations(scene_id)
        total_lines = len(await context.load_scene_lines(scene_id))
        translated = context.get_translated_line_count(scene_id)
        return (
            f"Scene {scene_id}: {translated}/{total_lines} lines translated "
            f"({_get_completion_ratio(translated, total_lines)})"
        )

    return [get_context_status, get_scene_completion, get_translation_progress]
