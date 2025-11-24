"""Tools for character-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.tools.hitl import request_if_human_authored

logger = get_logger(__name__)


def build_character_tools(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
) -> list:
    """Construct tools usable across characters.

    Returns:
        list: Tool callables ready to supply to ``create_agent``.
    """
    updated_name_tgt: set[str] = set()
    updated_pronouns: set[str] = set()
    updated_notes: set[str] = set()

    @tool("read_character")
    def read_character(character_id: str) -> str:
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

    @tool("list_context_docs")
    async def list_context_docs() -> str:
        """Return the available context document names."""
        docs = await context.list_context_docs()
        return "\n".join(docs) if docs else "(no context docs)"

    @tool("read_context_doc")
    async def read_context_doc(filename: str) -> str:
        """Return the contents of a context document."""
        return await context.read_context_doc(filename)

    @tool("update_character_name_tgt")
    async def update_character_name_tgt(character_id: str, name_tgt: str) -> str:
        """Update the target language name for this character.

        Args:
            character_id: Character identifier.
            name_tgt: Localized name in the target language.

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

    @tool("update_character_pronouns")
    async def update_character_pronouns(character_id: str, pronouns: str) -> str:
        """Update pronoun preferences for this character.

        Args:
            character_id: Character identifier.
            pronouns: Pronoun preferences (e.g., "she/her", "he/him", "they/them").

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

    @tool("update_character_notes")
    async def update_character_notes(character_id: str, notes: str) -> str:
        """Update character notes (personality, speech patterns, translation guidance).

        Args:
            character_id: Character identifier.
            notes: Character notes describing personality, speech style, quirks, etc.

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

    return [
        read_character,
        list_context_docs,
        read_context_doc,
        update_character_name_tgt,
        update_character_pronouns,
        update_character_notes,
    ]
