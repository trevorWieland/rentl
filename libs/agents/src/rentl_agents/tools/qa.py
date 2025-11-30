"""QA tools for editor subagents."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


def _build_read_tools(context: ProjectContext) -> tuple:
    """Return reusable read-only QA tools bound to a project context."""

    @tool("read_translations")
    async def read_translations(scene_id: str) -> str:
        """Return translated lines for a scene."""
        logger.info("Tool call: read_translations(scene_id=%s)", scene_id)
        translations = await context.get_translations(scene_id)
        if not translations:
            return f"No translations found for scene {scene_id}."

        rows = [f"{t.id} | SRC: {t.text_src} | TGT: {t.text_tgt}" for t in translations]
        return "\n".join(rows)

    @tool("read_style_guide")
    async def read_style_guide() -> str:
        """Return the project style guide content."""
        logger.info("Tool call: read_style_guide()")
        return await context.read_style_guide()

    @tool("get_ui_settings")
    def get_ui_settings() -> str:
        """Return UI constraints from game metadata."""
        logger.info("Tool call: get_ui_settings()")
        ui = context.get_ui_config()
        if not ui:
            return "No UI settings configured."
        return "\n".join(f"{k}: {v}" for k, v in ui.items())

    return read_translations, read_style_guide, get_ui_settings


def _build_record_tool(
    context: ProjectContext,
    *,
    tool_name: str,
    check_type: str,
    origin: str,
) -> BaseTool:
    """Return a context-bound tool that records QA checks."""

    @tool(tool_name)
    async def record_check(scene_id: str, line_id: str, passed: bool, note: str | None = None) -> str:
        """Record a quality check result for a translated line.

        Returns:
            str: Confirmation message after recording the check.
        """
        logger.info("Tool call: %s(scene_id=%s, line_id=%s)", tool_name, scene_id, line_id)
        return await context.add_translation_check(scene_id, line_id, check_type, passed, note, origin)

    return record_check


def build_style_check_tools(context: ProjectContext) -> list:
    """Tools for style checker agents.

    Returns:
        list: Bound tools including reads and record_style_check.
    """
    read_translations, read_style_guide, get_ui_settings = _build_read_tools(context)
    record_style_check = _build_record_tool(
        context,
        tool_name="record_style_check",
        check_type="style_check",
        origin="agent:style_checker",
    )
    return [read_translations, read_style_guide, get_ui_settings, record_style_check]


def build_consistency_check_tools(context: ProjectContext) -> list:
    """Tools for consistency checker agents.

    Returns:
        list: Bound tools including reads and record_consistency_check.
    """
    read_translations, _, _ = _build_read_tools(context)
    record_consistency_check = _build_record_tool(
        context,
        tool_name="record_consistency_check",
        check_type="consistency_check",
        origin="agent:consistency_checker",
    )
    return [read_translations, record_consistency_check]


def build_translation_review_tools(context: ProjectContext) -> list:
    """Tools for translation reviewer agents.

    Returns:
        list: Bound tools including reads and record_translation_review.
    """
    read_translations, read_style_guide, get_ui_settings = _build_read_tools(context)
    record_translation_review = _build_record_tool(
        context,
        tool_name="record_translation_review",
        check_type="translation_review",
        origin="agent:translation_reviewer",
    )
    return [read_translations, read_style_guide, get_ui_settings, record_translation_review]


def build_qa_tools(context: ProjectContext) -> list:
    """Return all QA tools for unit tests and composite agents."""
    read_translations, read_style_guide, get_ui_settings = _build_read_tools(context)
    return [
        read_translations,
        read_style_guide,
        get_ui_settings,
        _build_record_tool(
            context,
            tool_name="record_style_check",
            check_type="style_check",
            origin="agent:style_checker",
        ),
        _build_record_tool(
            context,
            tool_name="record_consistency_check",
            check_type="consistency_check",
            origin="agent:consistency_checker",
        ),
        _build_record_tool(
            context,
            tool_name="record_translation_review",
            check_type="translation_review",
            origin="agent:translation_reviewer",
        ),
    ]
