"""Tools for character-aware agents."""

from __future__ import annotations

from langchain_core.tools import tool
from rentl_core.context.project import ProjectContext


def build_character_tools(
    context: ProjectContext,
    character_id: str,
    *,
    allow_overwrite: bool = False,
) -> list:
    """Construct tools bound to a specific character.

    Returns:
        list: Tool callables ready to supply to ``create_deep_agent``.
    """
    character = context.get_character(character_id)

    @tool("read_character")
    def read_character() -> str:
        """Return current metadata for this character."""
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

    has_updated_name_tgt = False
    has_updated_pronouns = False
    has_updated_notes = False

    @tool("update_character_name_tgt")
    async def update_character_name_tgt(name_tgt: str) -> str:
        """Update the target language name for this character.

        Args:
            name_tgt: Localized name in the target language.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_updated_name_tgt
        if has_updated_name_tgt:
            return "Target name already updated. Provide a final assistant response."

        await context.update_character_name_tgt(character_id, name_tgt, allow_overwrite=allow_overwrite)
        has_updated_name_tgt = True
        return "Target name updated."

    @tool("update_character_pronouns")
    async def update_character_pronouns(pronouns: str) -> str:
        """Update pronoun preferences for this character.

        Args:
            pronouns: Pronoun preferences (e.g., "she/her", "he/him", "they/them").

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_updated_pronouns
        if has_updated_pronouns:
            return "Pronouns already updated. Provide a final assistant response."

        await context.update_character_pronouns(character_id, pronouns, allow_overwrite=allow_overwrite)
        has_updated_pronouns = True
        return "Pronouns updated."

    @tool("update_character_notes")
    async def update_character_notes(notes: str) -> str:
        """Update character notes (personality, speech patterns, translation guidance).

        Args:
            notes: Character notes describing personality, speech style, quirks, etc.

        Returns:
            str: Confirmation message after persistence.
        """
        nonlocal has_updated_notes
        if has_updated_notes:
            return "Notes already updated. Provide a final assistant response."

        await context.update_character_notes(character_id, notes, allow_overwrite=allow_overwrite)
        has_updated_notes = True
        return "Notes updated."

    return [
        read_character,
        list_context_docs,
        read_context_doc,
        update_character_name_tgt,
        update_character_pronouns,
        update_character_notes,
    ]
