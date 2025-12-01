"""Shared character tool implementations."""

from __future__ import annotations

from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def character_read_entry(context: ProjectContext, character_id: str) -> str:
    """Return current metadata for this character."""
    logger.info("Tool call: character_read_entry(character_id=%s)", character_id)
    character = context.get_character(character_id)
    parts = [
        f"Character ID: {character.id}",
        f"Source Name: {character.name_src}",
        f"Target Name: {character.name_tgt or '(not set)'}",
        f"Pronouns: {character.pronouns or '(not set)'}",
        f"Notes: {character.notes or '(not set)'}",
    ]
    return "\n".join(parts)


async def character_create_entry(
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

    logger.info("Tool call: character_create_entry(character_id=%s)", character_id)
    origin = f"agent:character_detailer:{date.today().isoformat()}"
    return await context.add_character(
        character_id,
        name_src,
        name_tgt=name_tgt,
        pronouns=pronouns,
        notes=notes,
        origin=origin,
    )


async def character_update_name_tgt(
    context: ProjectContext, character_id: str, name_tgt: str, *, updated_name_tgt: set[str]
) -> str:
    """Update the target language name for this character.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if character_id in updated_name_tgt:
        return "Target name already updated. Provide a final assistant response."

    logger.info("Tool call: character_update_name_tgt(character_id=%s)", character_id)
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


async def character_update_pronouns(
    context: ProjectContext, character_id: str, pronouns: str, *, updated_pronouns: set[str]
) -> str:
    """Update pronoun preferences for this character.

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if character_id in updated_pronouns:
        return "Pronouns already updated. Provide a final assistant response."

    logger.info("Tool call: character_update_pronouns(character_id=%s)", character_id)
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


async def character_update_notes(
    context: ProjectContext, character_id: str, notes: str, *, updated_notes: set[str]
) -> str:
    """Update character notes (personality, speech patterns, translation guidance).

    Returns:
        str: Confirmation message after persistence.
    """
    from datetime import date

    if character_id in updated_notes:
        return "Notes already updated. Provide a final assistant response."

    logger.info("Tool call: character_update_notes(character_id=%s)", character_id)
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


async def character_delete_entry(context: ProjectContext, character_id: str) -> str:
    """Delete a character entry with HITL protection for human-authored fields.

    Returns:
        str: Status or approval message.
    """
    character = context.characters.get(character_id)
    if not character:
        return f"Character '{character_id}' not found."

    if any(
        origin == "human"
        for origin in (
            character.name_src_origin,
            character.name_tgt_origin,
            character.pronouns_origin,
            character.notes_origin,
        )
    ):
        return f"APPROVAL REQUIRED to delete character '{character_id}' with human-authored fields."

    logger.info("Tool call: character_delete_entry(character_id=%s)", character_id)
    return await context.delete_character(character_id)
