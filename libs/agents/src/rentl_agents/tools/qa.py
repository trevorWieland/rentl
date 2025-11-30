"""QA tools for editor subagents."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


async def read_translations(context: ProjectContext, scene_id: str) -> str:
    """Return translated lines for a scene."""
    logger.info("Tool call: read_translations(scene_id=%s)", scene_id)
    translations = await context.get_translations(scene_id)
    if not translations:
        return f"No translations found for scene {scene_id}."

    rows = [f"{t.id} | SRC: {t.text_src} | TGT: {t.text_tgt}" for t in translations]
    return "\n".join(rows)


async def read_style_guide(context: ProjectContext) -> str:
    """Return the project style guide content."""
    logger.info("Tool call: read_style_guide()")
    return await context.read_style_guide()


def get_ui_settings(context: ProjectContext) -> str:
    """Return UI constraints from game metadata."""
    logger.info("Tool call: get_ui_settings()")
    ui = context.get_ui_config()
    if not ui:
        return "No UI settings configured."
    return "\n".join(f"{k}: {v}" for k, v in ui.items())


async def record_translation_check(
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


def build_style_check_tools(context: ProjectContext) -> list[BaseTool]:
    """Tools for style checker agents.

    Returns:
        list[BaseTool]: Bound tools including reads and record_style_check.
    """

    @tool("read_translations")
    async def read_translations_tool(scene_id: str) -> str:
        """Return translated lines for a scene."""
        return await read_translations(context, scene_id)

    @tool("read_style_guide")
    async def read_style_guide_tool() -> str:
        """Return the project style guide content."""
        return await read_style_guide(context)

    @tool("get_ui_settings")
    def get_ui_settings_tool() -> str:
        """Return UI constraints from game metadata."""
        return get_ui_settings(context)

    @tool("record_style_check")
    async def record_style_check_tool(scene_id: str, line_id: str, passed: bool, note: str | None = None) -> str:
        """Record a style check result for a translated line.

        Returns:
            str: Confirmation message after recording the check.
        """
        return await record_translation_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="style_check",
            origin="agent:style_checker",
        )

    return [read_translations_tool, read_style_guide_tool, get_ui_settings_tool, record_style_check_tool]


def build_consistency_check_tools(context: ProjectContext) -> list[BaseTool]:
    """Tools for consistency checker agents.

    Returns:
        list[BaseTool]: Bound tools including reads and record_consistency_check.
    """

    @tool("read_translations")
    async def read_translations_tool(scene_id: str) -> str:
        """Return translated lines for a scene."""
        return await read_translations(context, scene_id)

    @tool("record_consistency_check")
    async def record_consistency_check_tool(scene_id: str, line_id: str, passed: bool, note: str | None = None) -> str:
        """Record a consistency check result for a translated line.

        Returns:
            str: Confirmation message after recording the check.
        """
        return await record_translation_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="consistency_check",
            origin="agent:consistency_checker",
        )

    return [read_translations_tool, record_consistency_check_tool]


def build_translation_review_tools(context: ProjectContext) -> list[BaseTool]:
    """Tools for translation reviewer agents.

    Returns:
        list[BaseTool]: Bound tools including reads and record_translation_review.
    """

    @tool("read_translations")
    async def read_translations_tool(scene_id: str) -> str:
        """Return translated lines for a scene."""
        return await read_translations(context, scene_id)

    @tool("read_style_guide")
    async def read_style_guide_tool() -> str:
        """Return the project style guide content."""
        return await read_style_guide(context)

    @tool("get_ui_settings")
    def get_ui_settings_tool() -> str:
        """Return UI constraints from game metadata."""
        return get_ui_settings(context)

    @tool("record_translation_review")
    async def record_translation_review_tool(scene_id: str, line_id: str, passed: bool, note: str | None = None) -> str:
        """Record a translation review result for a translated line.

        Returns:
            str: Confirmation message after recording the check.
        """
        return await record_translation_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="translation_review",
            origin="agent:translation_reviewer",
        )

    return [
        read_translations_tool,
        read_style_guide_tool,
        get_ui_settings_tool,
        record_translation_review_tool,
    ]


def build_qa_tools(context: ProjectContext) -> list[BaseTool]:
    """Return all QA tools for unit tests and composite agents."""
    style_tools = build_style_check_tools(context)
    consistency_tools = build_consistency_check_tools(context)
    review_tools = build_translation_review_tools(context)
    # Deduplicate by name while preserving order
    seen: set[str] = set()
    merged: list[BaseTool] = []
    for tool_obj in [*style_tools, *consistency_tools, *review_tools]:
        name = getattr(tool_obj, "name", "")
        if name in seen:
            continue
        seen.add(name)
        merged.append(tool_obj)
    return merged
