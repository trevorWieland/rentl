"""Tools for character-aware agents."""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.context_docs import build_context_doc_tools
from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def read_character(context: ProjectContext, character_id: str) -> str:
    """Return current metadata for this character."""
    logger.info("Tool call: read_character(character_id=%s)", character_id)
    character = context.get_character(character_id)
    parts = [
        f"Character ID: {character.id}",
        f"Source Name: {character.name_src}",
        f"Target Name: {character.name_tgt or '(not set)'}",
        f"Pronouns: {character.pronouns or '(not set)'}",
        f"Notes: {character.notes or '(not set)'}",
    ]
    return "\n".join(parts)


async def add_character(
    context: ProjectContext,
    character_id: str,
    name_src: str,
    name_tgt: str | None = None,
    pronouns: str | None = None,
    notes: str | None = None,
) -> str:
    """Add a new character entry with provenance tracking.

    Returns:
        str: Status message after attempting creation.
    """
    from datetime import date

    logger.info("Tool call: add_character(character_id=%s)", character_id)
    origin = f"agent:character_detailer:{date.today().isoformat()}"
    return await context.add_character(
        character_id,
        name_src,
        name_tgt=name_tgt,
        pronouns=pronouns,
        notes=notes,
        origin=origin,
    )


async def update_character_name_tgt(
    context: ProjectContext, character_id: str, name_tgt: str, *, updated_name_tgt: set[str]
) -> str:
    """Update the target language name for this character.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if character_id in updated_name_tgt:
        return "Target name already updated. Provide a final assistant response."

    logger.info("Tool call: update_character_name_tgt(character_id=%s)", character_id)
    character = context.get_character(character_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"character.{character_id}.name_tgt",
        current_value=character.name_tgt,
        current_origin=character.name_tgt_origin,
        proposed_value=name_tgt,
    )
    if approval:
        return approval

    origin = f"agent:character_detailer:{date.today().isoformat()}"
    result = await context.update_character_name_tgt(character_id, name_tgt, origin)
    updated_name_tgt.add(character_id)
    return result


async def update_character_pronouns(
    context: ProjectContext, character_id: str, pronouns: str, *, updated_pronouns: set[str]
) -> str:
    """Update pronoun preferences for this character.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if character_id in updated_pronouns:
        return "Pronouns already updated. Provide a final assistant response."

    logger.info("Tool call: update_character_pronouns(character_id=%s)", character_id)
    character = context.get_character(character_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"character.{character_id}.pronouns",
        current_value=character.pronouns,
        current_origin=character.pronouns_origin,
        proposed_value=pronouns,
    )
    if approval:
        return approval

    origin = f"agent:character_detailer:{date.today().isoformat()}"
    result = await context.update_character_pronouns(character_id, pronouns, origin)
    updated_pronouns.add(character_id)
    return result


async def update_character_notes(
    context: ProjectContext, character_id: str, notes: str, *, updated_notes: set[str]
) -> str:
    """Update character notes (personality, speech patterns, translation guidance).

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if character_id in updated_notes:
        return "Notes already updated. Provide a final assistant response."

    logger.info("Tool call: update_character_notes(character_id=%s)", character_id)
    character = context.get_character(character_id)
    approval = request_if_human_authored(
        operation="update",
        target=f"character.{character_id}.notes",
        current_value=character.notes,
        current_origin=character.notes_origin,
        proposed_value=notes,
    )
    if approval:
        return approval

    origin = f"agent:character_detailer:{date.today().isoformat()}"
    result = await context.update_character_notes(character_id, notes, origin)
    updated_notes.add(character_id)
    return result


def build_character_tools(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
) -> list[BaseTool]:
    """Construct tools usable across characters.

    Returns:
        list[BaseTool]: Tool callables ready to supply to ``create_agent``.
    """
    updated_name_tgt: set[str] = set()
    updated_pronouns: set[str] = set()
    updated_notes: set[str] = set()
    context_doc_tools = build_context_doc_tools(context)

    @tool("read_character")
    def read_character_tool(character_id: str) -> str:
        """Return current metadata for this character."""
        return read_character(context, character_id)

    @tool("add_character")
    async def add_character_tool(
        character_id: str,
        name_src: str,
        name_tgt: str | None = None,
        pronouns: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Add a new character entry with provenance tracking.

        Returns:
            str: Status message after attempting creation.
        """
        return await add_character(
            context,
            character_id,
            name_src,
            name_tgt=name_tgt,
            pronouns=pronouns,
            notes=notes,
        )

    @tool("update_character_name_tgt")
    async def update_character_name_tgt_tool(character_id: str, name_tgt: str) -> str:
        """Update the target language name for this character.

        Returns:
            str: Confirmation message after persistence.
        """
        return await update_character_name_tgt(context, character_id, name_tgt, updated_name_tgt=updated_name_tgt)

    @tool("update_character_pronouns")
    async def update_character_pronouns_tool(character_id: str, pronouns: str) -> str:
        """Update pronoun preferences for this character.

        Returns:
            str: Confirmation message after persistence.
        """
        return await update_character_pronouns(context, character_id, pronouns, updated_pronouns=updated_pronouns)

    @tool("update_character_notes")
    async def update_character_notes_tool(character_id: str, notes: str) -> str:
        """Update character notes (personality, speech patterns, translation guidance).

        Returns:
            str: Confirmation message after persistence.
        """
        return await update_character_notes(context, character_id, notes, updated_notes=updated_notes)

    return [
        read_character_tool,
        add_character_tool,
        *context_doc_tools,
        update_character_name_tgt_tool,
        update_character_pronouns_tool,
        update_character_notes_tool,
    ]
