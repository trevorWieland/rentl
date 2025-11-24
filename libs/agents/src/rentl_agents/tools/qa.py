"""QA tools for editor subagents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext


@tool("read_translations")
async def read_translations(context: ProjectContext, scene_id: str) -> str:
    """Return translated lines for a scene."""
    translations = await context.get_translations(scene_id)
    if not translations:
        return f"No translations found for scene {scene_id}."

    rows = [f"{t.id} | SRC: {t.text_src} | TGT: {t.text_tgt}" for t in translations]
    return "\n".join(rows)


@tool("read_style_guide")
async def read_style_guide(context: ProjectContext) -> str:
    """Return the project style guide content."""
    return await context.read_style_guide()


@tool("get_ui_settings")
def get_ui_settings(context: ProjectContext) -> str:
    """Return UI constraints from game metadata."""
    ui = context.get_ui_config()
    if not ui:
        return "No UI settings configured."
    return "\n".join(f"{k}: {v}" for k, v in ui.items())


@tool("record_style_check")
async def record_style_check(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    passed: bool,
    note: str | None = None,
) -> str:
    """Record a style check result for a translated line.

    Returns:
        str: Status message after recording.
    """
    origin = "agent:style_checker"
    return await context.add_translation_check(scene_id, line_id, "style_check", passed, note, origin)


@tool("record_consistency_check")
async def record_consistency_check(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    passed: bool,
    note: str | None = None,
) -> str:
    """Record a consistency check result for a translated line.

    Returns:
        str: Status message after recording.
    """
    origin = "agent:consistency_checker"
    return await context.add_translation_check(scene_id, line_id, "consistency_check", passed, note, origin)


@tool("record_translation_review")
async def record_translation_review(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    passed: bool,
    note: str | None = None,
) -> str:
    """Record a translation review result for a translated line.

    Returns:
        str: Status message after recording.
    """
    origin = "agent:translation_reviewer"
    return await context.add_translation_check(scene_id, line_id, "translation_review", passed, note, origin)
