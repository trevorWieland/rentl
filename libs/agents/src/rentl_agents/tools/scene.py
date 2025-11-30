"""Shared scene tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


async def read_scene(context: ProjectContext, scene_id: str) -> str:
    """Return metadata and transcript for the scene (no redactions)."""
    logger.info("Tool call: read_scene(scene_id=%s)", scene_id)
    lines = await context.load_scene_lines(scene_id)
    scene = context.get_scene(scene_id)

    formatted_rows: list[str] = []
    for idx, line in enumerate(lines, start=1):
        speaker = line.meta.speaker or "Narration"
        prefix = "[CHOICE] " if line.is_choice else ""
        notes = f" (notes: {'; '.join(line.meta.style_notes)})" if line.meta.style_notes else ""
        formatted_rows.append(f"{idx}. {line.id} | {prefix}{speaker}: {line.text}{notes}")
    transcript = "\n".join(formatted_rows)

    meta = [
        f"Title: {scene.title}",
        f"Routes: {', '.join(scene.route_ids)}",
        f"Tags: {', '.join(scene.annotations.tags)}",
        f"Primary Characters: {', '.join(scene.annotations.primary_characters)}",
        f"Locations: {', '.join(scene.annotations.locations)}",
    ]
    if scene.annotations.summary:
        meta.extend(["Summary:", scene.annotations.summary])
    meta.extend(["Transcript:", transcript])
    return "\n".join(meta)


async def read_scene_overview(context: ProjectContext, scene_id: str, *, allow_overwrite: bool = False) -> str:
    """Return metadata and transcript for the scene."""
    logger.info("Tool call: read_scene_overview(scene_id=%s)", scene_id)
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


async def write_scene_summary(
    context: ProjectContext, scene_id: str, summary: str, *, written_summary: set[str]
) -> str:
    """Store the final summary for this scene.

    Returns:
        str: Confirmation or approval message.
    """
    from datetime import date

    if scene_id in written_summary:
        return "Summary already stored. Provide a final assistant response."

    scene = context.get_scene(scene_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"scene.{scene_id}.summary",
        current_value=scene.annotations.summary,
        current_origin=scene.annotations.summary_origin,
        proposed_value=summary,
    )
    if approval:
        return approval

    logger.info("Tool call: write_scene_summary(scene_id=%s)", scene_id)
    origin = f"agent:scene_detailer:{date.today().isoformat()}"
    result = await context.set_scene_summary(scene_id, summary, origin)
    written_summary.add(scene_id)
    return result


async def write_scene_tags(context: ProjectContext, scene_id: str, tags: list[str], *, written_tags: set[str]) -> str:
    """Store tags for this scene.

    Returns:
        str: Confirmation or approval message.
    """
    from datetime import date

    if scene_id in written_tags:
        return "Tags already stored. Provide a final assistant response."

    scene = context.get_scene(scene_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"scene.{scene_id}.tags",
        current_value=scene.annotations.tags,
        current_origin=scene.annotations.tags_origin,
        proposed_value=tags,
    )
    if approval:
        return approval

    logger.info("Tool call: write_scene_tags(scene_id=%s)", scene_id)
    origin = f"agent:scene_detailer:{date.today().isoformat()}"
    result = await context.set_scene_tags(scene_id, tags, origin)
    written_tags.add(scene_id)
    return result


async def write_primary_characters(
    context: ProjectContext, scene_id: str, character_ids: list[str], *, written_characters: set[str]
) -> str:
    """Store primary characters identified in this scene.

    Returns:
        str: Confirmation or approval message.
    """
    from datetime import date

    if scene_id in written_characters:
        return "Characters already stored. Provide a final assistant response."

    scene = context.get_scene(scene_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"scene.{scene_id}.primary_characters",
        current_value=scene.annotations.primary_characters,
        current_origin=scene.annotations.primary_characters_origin,
        proposed_value=character_ids,
    )
    if approval:
        return approval

    logger.info("Tool call: write_primary_characters(scene_id=%s)", scene_id)
    origin = f"agent:scene_detailer:{date.today().isoformat()}"
    result = await context.set_scene_characters(scene_id, character_ids, origin)
    written_characters.add(scene_id)
    return result


async def write_scene_locations(
    context: ProjectContext, scene_id: str, location_ids: list[str], *, written_locations: set[str]
) -> str:
    """Store locations identified in this scene.

    Returns:
        str: Confirmation or approval message.
    """
    from datetime import date

    if scene_id in written_locations:
        return "Locations already stored. Provide a final assistant response."

    scene = context.get_scene(scene_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"scene.{scene_id}.locations",
        current_value=scene.annotations.locations,
        current_origin=scene.annotations.locations_origin,
        proposed_value=location_ids,
    )
    if approval:
        return approval

    logger.info("Tool call: write_scene_locations(scene_id=%s)", scene_id)
    origin = f"agent:scene_detailer:{date.today().isoformat()}"
    result = await context.set_scene_locations(scene_id, location_ids, origin)
    written_locations.add(scene_id)
    return result
