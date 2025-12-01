"""Test-only tool builders to wrap shared tool implementations.

These helpers keep unit tests aligned with the shared tool functions now that
production modules no longer expose build_* helpers.
"""

from __future__ import annotations

from datetime import date

from langchain_core.tools import BaseTool, tool
from rentl_agents.subagents.meta_glossary_curator import _build_glossary_curator_tools
from rentl_agents.subagents.translate_scene import _build_scene_translator_tools
from rentl_agents.tools.character import (
    character_create_entry,
    character_delete_entry,
    character_read_entry,
    character_update_name_tgt,
    character_update_notes,
    character_update_pronouns,
)
from rentl_agents.tools.context_docs import contextdoc_list_all, contextdoc_read_doc
from rentl_agents.tools.location import (
    location_create_entry,
    location_delete_entry,
    location_read_entry,
    location_update_description,
    location_update_name_tgt,
)
from rentl_agents.tools.qa import (
    styleguide_read_full,
    translation_create_check,
    translation_create_consistency_check,
    translation_create_review_check,
    translation_create_style_check,
    translation_read_scene,
    ui_read_settings,
)
from rentl_agents.tools.route import (
    route_create_entry,
    route_delete_entry,
    route_read_entry,
    route_update_primary_characters,
    route_update_synopsis,
)
from rentl_agents.tools.scene import (
    scene_read_overview,
    scene_update_locations,
    scene_update_primary_characters,
    scene_update_summary,
    scene_update_tags,
)
from rentl_agents.tools.stats import (
    character_read_progress,
    context_read_status,
    route_read_progress,
    scene_read_progress,
    translation_read_progress,
)
from rentl_core.context.project import ProjectContext


def build_scene_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return scene tools matching the single-purpose scene detailers."""
    written_summary: set[str] = set()
    written_tags: set[str] = set()
    written_characters: set[str] = set()
    written_locations: set[str] = set()

    @tool("scene_read_overview")
    async def scene_read_overview_tool(scene_id: str) -> str:
        """Return scene overview."""
        return await scene_read_overview(context, scene_id)

    @tool("scene_update_summary")
    async def scene_update_summary_tool(scene_id: str, summary: str) -> str:
        """Update scene summary.

        Returns:
            str: Status message.
        """
        return await scene_update_summary(context, scene_id, summary, written_summary=written_summary)

    @tool("scene_update_tags")
    async def scene_update_tags_tool(scene_id: str, tags: list[str]) -> str:
        """Update scene tags.

        Returns:
            str: Status message.
        """
        return await scene_update_tags(context, scene_id, tags, written_tags=written_tags)

    @tool("scene_update_primary_characters")
    async def scene_update_primary_characters_tool(scene_id: str, character_ids: list[str]) -> str:
        """Update primary characters for scene.

        Returns:
            str: Status message.
        """
        return await scene_update_primary_characters(
            context, scene_id, character_ids, written_characters=written_characters
        )

    @tool("scene_update_locations")
    async def scene_update_locations_tool(scene_id: str, location_ids: list[str]) -> str:
        """Update locations for scene.

        Returns:
            str: Status message.
        """
        return await scene_update_locations(context, scene_id, location_ids, written_locations=written_locations)

    return [
        scene_read_overview_tool,
        scene_update_summary_tool,
        scene_update_tags_tool,
        scene_update_primary_characters_tool,
        scene_update_locations_tool,
    ]


def build_character_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return character tools matching the meta_character_curator toolbox."""
    updated_name_tgt: set[str] = set()
    updated_pronouns: set[str] = set()
    updated_notes: set[str] = set()

    @tool("character_read_entry")
    def read_character_tool(character_id: str) -> str:
        """Return character metadata for testing.

        Returns:
            str: Character detail string.
        """
        return character_read_entry(context, character_id)

    @tool("character_create_entry")
    async def add_character_tool(
        character_id: str,
        name_src: str,
        name_tgt: str | None = None,
        pronouns: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Create a character entry.

        Returns:
            str: Status message.
        """
        return await character_create_entry(
            context,
            character_id,
            name_src,
            name_tgt=name_tgt,
            pronouns=pronouns,
            notes=notes,
        )

    @tool("character_update_name_tgt")
    async def update_character_name_tgt_tool(character_id: str, name_tgt: str) -> str:
        """Update character target name.

        Returns:
            str: Status message.
        """
        return await character_update_name_tgt(context, character_id, name_tgt, updated_name_tgt=updated_name_tgt)

    @tool("character_update_pronouns")
    async def update_character_pronouns_tool(character_id: str, pronouns: str) -> str:
        """Update character pronouns.

        Returns:
            str: Status message.
        """
        return await character_update_pronouns(context, character_id, pronouns, updated_pronouns=updated_pronouns)

    @tool("character_update_notes")
    async def update_character_notes_tool(character_id: str, notes: str) -> str:
        """Update character notes.

        Returns:
            str: Status message.
        """
        return await character_update_notes(context, character_id, notes, updated_notes=updated_notes)

    @tool("character_delete_entry")
    async def delete_character_tool(character_id: str) -> str:
        """Delete a character entry.

        Returns:
            str: Status message.
        """
        return await character_delete_entry(context, character_id)

    return [
        read_character_tool,
        add_character_tool,
        update_character_name_tgt_tool,
        update_character_pronouns_tool,
        update_character_notes_tool,
        delete_character_tool,
    ]


def build_location_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return location tools matching the meta_location_curator toolbox."""
    updated_name_tgt: set[str] = set()
    updated_description: set[str] = set()

    @tool("location_read_entry")
    def read_location_tool(location_id: str) -> str:
        """Return location metadata for testing.

        Returns:
            str: Location detail string.
        """
        return location_read_entry(context, location_id)

    @tool("location_create_entry")
    async def add_location_tool(
        location_id: str,
        name_src: str,
        name_tgt: str | None = None,
        description: str | None = None,
    ) -> str:
        """Create a location entry.

        Returns:
            str: Status message.
        """
        return await location_create_entry(
            context,
            location_id,
            name_src,
            name_tgt=name_tgt,
            description=description,
        )

    @tool("location_update_name_tgt")
    async def update_location_name_tgt_tool(location_id: str, name_tgt: str) -> str:
        """Update the target language location name.

        Returns:
            str: Status message.
        """
        return await location_update_name_tgt(context, location_id, name_tgt, updated_name_tgt=updated_name_tgt)

    @tool("location_update_description")
    async def update_location_description_tool(location_id: str, description: str) -> str:
        """Update the location description.

        Returns:
            str: Status message.
        """
        return await location_update_description(
            context, location_id, description, updated_description=updated_description
        )

    @tool("location_delete_entry")
    async def delete_location_tool(location_id: str) -> str:
        """Delete a location entry.

        Returns:
            str: Status message.
        """
        return await location_delete_entry(context, location_id)

    return [
        read_location_tool,
        add_location_tool,
        update_location_name_tgt_tool,
        update_location_description_tool,
        delete_location_tool,
    ]


def build_route_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return route tools matching the route_outline_builder toolbox."""
    updated_synopsis: set[str] = set()
    updated_characters: set[str] = set()

    @tool("route_read_entry")
    def read_route_tool(route_id: str) -> str:
        """Return route metadata for testing.

        Returns:
            str: Route detail string.
        """
        return route_read_entry(context, route_id)

    @tool("route_create_entry")
    async def create_route_tool(route_id: str, name: str, scene_ids: list[str] | None = None) -> str:
        """Create a new route entry.

        Returns:
            str: Status message.
        """
        return await route_create_entry(context, route_id, name, scene_ids or [])

    @tool("route_update_synopsis")
    async def update_route_synopsis_tool(route_id: str, synopsis: str) -> str:
        """Update the route synopsis.

        Returns:
            str: Status message.
        """
        return await route_update_synopsis(context, route_id, synopsis, updated_synopsis=updated_synopsis)

    @tool("route_update_primary_characters")
    async def update_route_characters_tool(route_id: str, character_ids: list[str]) -> str:
        """Update primary characters for a route.

        Returns:
            str: Status message.
        """
        return await route_update_primary_characters(
            context, route_id, character_ids, updated_characters=updated_characters
        )

    @tool("route_delete_entry")
    async def delete_route_tool(route_id: str) -> str:
        """Delete a route entry.

        Returns:
            str: Status message.
        """
        return await route_delete_entry(context, route_id)

    return [
        read_route_tool,
        create_route_tool,
        update_route_synopsis_tool,
        update_route_characters_tool,
        delete_route_tool,
    ]


def build_glossary_tools(context: ProjectContext, *, allow_overwrite: bool = False) -> list[BaseTool]:
    """Return glossary tools matching the meta_glossary_curator toolbox."""
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

    @tool("translation_read_scene")
    async def read_translations_tool(scene_id: str) -> str:
        """Return translated lines for a scene."""
        return await translation_read_scene(context, scene_id)

    @tool("styleguide_read_full")
    async def read_style_guide_tool() -> str:
        """Return the project style guide content."""
        return await styleguide_read_full(context)

    @tool("ui_read_settings")
    def get_ui_settings_tool() -> str:
        """Return UI constraints from game metadata."""
        return ui_read_settings(context)

    @tool("translation_create_check")
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
        return await translation_create_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="qa_check",
            origin=origin,
        )

    @tool("translation_create_style_check")
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
        return await translation_create_style_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            origin=origin,
        )

    @tool("translation_create_consistency_check")
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
        return await translation_create_consistency_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            origin=origin,
        )

    @tool("translation_create_review_check")
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
        return await translation_create_review_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
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

    @tool("context_read_status")
    def get_context_status_tool() -> str:
        """Summarize context completion counts.

        Returns:
            str: Status summary text.
        """
        return context_read_status(context)

    @tool("scene_read_progress")
    def get_scene_completion_tool(scene_id: str) -> str:
        """Return completion status for a scene."""
        return scene_read_progress(context, scene_id)

    @tool("character_read_progress")
    def get_character_completion_tool(character_id: str) -> str:
        """Return completion status for a character."""
        return character_read_progress(context, character_id)

    @tool("translation_read_progress")
    async def get_translation_progress_tool(scene_id: str) -> str:
        """Return overall translation progress."""
        return await translation_read_progress(context, scene_id)

    @tool("route_read_progress")
    def get_route_progress_tool(route_id: str) -> str:
        """Return progress summary for a route."""
        return route_read_progress(context, route_id)

    return [
        get_context_status_tool,
        get_scene_completion_tool,
        get_character_completion_tool,
        get_translation_progress_tool,
        get_route_progress_tool,
    ]


def build_context_doc_tools(context: ProjectContext) -> list[BaseTool]:
    """Return context document tools for tests."""

    @tool("contextdoc_list_all")
    async def list_context_docs_tool() -> str:
        """Return the available context document names."""
        return await contextdoc_list_all(context)

    @tool("contextdoc_read_doc")
    async def read_context_doc_tool(filename: str) -> str:
        """Return the contents of a context document."""
        return await contextdoc_read_doc(context, filename)

    return [list_context_docs_tool, read_context_doc_tool]
