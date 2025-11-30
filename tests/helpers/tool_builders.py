"""Test-only tool builders to wrap shared tool implementations.

These helpers keep unit tests aligned with the shared tool functions now that
production modules no longer expose build_* helpers.
"""

from __future__ import annotations

from datetime import date

from langchain_core.tools import BaseTool, tool
from rentl_agents.subagents.character_detailer import _build_character_detailer_tools
from rentl_agents.subagents.glossary_curator import _build_glossary_curator_tools
from rentl_agents.subagents.location_detailer import _build_location_detailer_tools
from rentl_agents.subagents.route_detailer import _build_route_detailer_tools
from rentl_agents.subagents.scene_detailer import _build_scene_detailer_tools
from rentl_agents.subagents.translate_scene import _build_scene_translator_tools
from rentl_agents.tools.context_docs import list_context_docs, read_context_doc
from rentl_agents.tools.qa import get_ui_settings, read_style_guide, read_translations, record_translation_check
from rentl_agents.tools.stats import (
    get_character_completion,
    get_context_status,
    get_route_progress,
    get_scene_completion,
    get_translation_progress,
)
from rentl_core.context.project import ProjectContext


def build_scene_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return scene tools matching the scene_detailer toolbox."""
    return _build_scene_detailer_tools(context, allow_overwrite=allow_overwrite)


def build_character_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return character tools matching the character_detailer toolbox."""
    return _build_character_detailer_tools(context, allow_overwrite=allow_overwrite)


def build_location_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return location tools matching the location_detailer toolbox."""
    return _build_location_detailer_tools(context, allow_overwrite=allow_overwrite)


def build_route_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return route tools matching the route_detailer toolbox."""
    return _build_route_detailer_tools(context, allow_overwrite=allow_overwrite)


def build_glossary_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return glossary tools matching the glossary_curator toolbox."""
    return _build_glossary_curator_tools(context, allow_overwrite=allow_overwrite)


def build_translation_tools(
    context: ProjectContext,
    *,
    agent_name: str = "unit_test",
    allow_overwrite: bool = False,
) -> list[BaseTool]:
    """Return translation tools matching the scene_translator toolbox."""
    return _build_scene_translator_tools(context, allow_overwrite=allow_overwrite, agent_name=agent_name)


def build_qa_tools(context: ProjectContext) -> list[BaseTool]:
    """Return QA tools for reading translations and config."""

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

    @tool("record_translation_check")
    async def record_translation_check_tool(
        scene_id: str,
        line_id: str,
        passed: bool,
        note: str | None = None,
    ) -> str:
        """Record a quality check result for a translated line.

        Returns:
            str: Confirmation message after storing the check.
        """
        origin = f"agent:test:{date.today().isoformat()}"
        return await record_translation_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="qa_check",
            origin=origin,
        )

    @tool("record_style_check")
    async def record_style_check_tool(
        scene_id: str,
        line_id: str,
        passed: bool,
        note: str | None = None,
    ) -> str:
        """Record a style check result.

        Returns:
            str: Confirmation message after storing the check.
        """
        origin = f"agent:test:{date.today().isoformat()}"
        return await record_translation_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="style_check",
            origin=origin,
        )

    @tool("record_consistency_check")
    async def record_consistency_check_tool(
        scene_id: str,
        line_id: str,
        passed: bool,
        note: str | None = None,
    ) -> str:
        """Record a consistency check result.

        Returns:
            str: Confirmation message after storing the check.
        """
        origin = f"agent:test:{date.today().isoformat()}"
        return await record_translation_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="consistency_check",
            origin=origin,
        )

    @tool("record_translation_review")
    async def record_translation_review_tool(
        scene_id: str,
        line_id: str,
        passed: bool,
        note: str | None = None,
    ) -> str:
        """Record a translation review result.

        Returns:
            str: Confirmation message after storing the check.
        """
        origin = f"agent:test:{date.today().isoformat()}"
        return await record_translation_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="translation_review",
            origin=origin,
        )

    return [
        read_translations_tool,
        read_style_guide_tool,
        get_ui_settings_tool,
        record_translation_check_tool,
        record_style_check_tool,
        record_consistency_check_tool,
        record_translation_review_tool,
    ]


def build_stats_tools(context: ProjectContext) -> list[BaseTool]:
    """Return stats tools wrapping shared implementations."""

    @tool("get_context_status")
    def get_context_status_tool() -> str:
        """Summarize context completion counts.

        Returns:
            str: Status summary text.
        """
        return get_context_status(context)

    @tool("get_scene_completion")
    def get_scene_completion_tool(scene_id: str) -> str:
        """Return completion status for a scene."""
        return get_scene_completion(context, scene_id)

    @tool("get_character_completion")
    def get_character_completion_tool(character_id: str) -> str:
        """Return completion status for a character."""
        return get_character_completion(context, character_id)

    @tool("get_translation_progress")
    async def get_translation_progress_tool(scene_id: str) -> str:
        """Return overall translation progress."""
        return await get_translation_progress(context, scene_id)

    @tool("get_route_progress")
    def get_route_progress_tool(route_id: str) -> str:
        """Return progress summary for a route."""
        return get_route_progress(context, route_id)

    return [
        get_context_status_tool,
        get_scene_completion_tool,
        get_character_completion_tool,
        get_translation_progress_tool,
        get_route_progress_tool,
    ]


def build_context_doc_tools(context: ProjectContext) -> list[BaseTool]:
    """Return context document tools for tests."""

    @tool("list_context_docs")
    async def list_context_docs_tool() -> str:
        """Return the available context document names."""
        return await list_context_docs(context)

    @tool("read_context_doc")
    async def read_context_doc_tool(filename: str) -> str:
        """Return the contents of a context document."""
        return await read_context_doc(context, filename)

    return [list_context_docs_tool, read_context_doc_tool]
