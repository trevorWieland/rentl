"""Shared QA tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


async def translation_read_scene(context: ProjectContext, scene_id: str) -> str:
    """Return translated lines for a scene.

    Returns:
        str: Translations formatted with IDs, source, and target.
    """
    logger.info("Tool call: translation_read_scene(scene_id=%s)", scene_id)
    translations = await context.get_translations(scene_id)
    if not translations:
        return f"No translations found for scene {scene_id}."

    rows = [f"{t.id} | SRC: {t.text_src} | TGT: {t.text_tgt}" for t in translations]
    return "\n".join(rows)


async def styleguide_read_full(context: ProjectContext) -> str:
    """Return the project style guide content.

    Returns:
        str: Style guide text or fallback message.
    """
    logger.info("Tool call: styleguide_read_full()")
    return await context.read_style_guide()


def ui_read_settings(context: ProjectContext) -> str:
    """Return UI constraints from game metadata.

    Returns:
        str: UI settings formatted as key: value lines.
    """
    logger.info("Tool call: ui_read_settings()")
    ui = context.get_ui_config()
    if not ui:
        return "No UI settings configured."
    return "\n".join(f"{k}: {v}" for k, v in ui.items())


async def translation_create_check(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    passed: bool,
    note: str | None,
    *,
    check_type: str,
    origin: str,
) -> str:
    """Record a quality check result for a translated line.

    Returns:
        str: Confirmation message after recording the check.
    """
    logger.info("Tool call: record_%s(scene_id=%s, line_id=%s)", check_type, scene_id, line_id)
    return await context.add_translation_check(scene_id, line_id, check_type, passed, note, origin)


async def translation_create_style_check(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    passed: bool,
    note: str | None,
    *,
    origin: str,
) -> str:
    """Record a style check result for a translated line.

    Returns:
        str: Confirmation message after recording the check.
    """
    return await translation_create_check(
        context,
        scene_id,
        line_id,
        passed,
        note,
        check_type="style_check",
        origin=origin,
    )


async def translation_create_consistency_check(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    passed: bool,
    note: str | None,
    *,
    origin: str,
) -> str:
    """Record a consistency check result for a translated line.

    Returns:
        str: Confirmation message after recording the check.
    """
    return await translation_create_check(
        context,
        scene_id,
        line_id,
        passed,
        note,
        check_type="consistency_check",
        origin=origin,
    )


async def translation_create_review_check(
    context: ProjectContext,
    scene_id: str,
    line_id: str,
    passed: bool,
    note: str | None,
    *,
    origin: str,
) -> str:
    """Record a fidelity/fluency review result for a translated line.

    Returns:
        str: Confirmation message after recording the check.
    """
    return await translation_create_check(
        context,
        scene_id,
        line_id,
        passed,
        note,
        check_type="translation_review",
        origin=origin,
    )
