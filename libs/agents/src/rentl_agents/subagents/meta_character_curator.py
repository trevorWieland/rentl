"""Character curator subagent (global metadata)."""

from __future__ import annotations

from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import BaseTool, tool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.hitl.checkpoints import get_default_checkpointer
from rentl_agents.hitl.invoke import Decision, run_with_human_loop
from rentl_agents.tools.character import (
    character_create_entry,
    character_delete_entry,
    character_read_entry,
    character_update_name_tgt,
    character_update_notes,
    character_update_pronouns,
)
from rentl_agents.tools.context_docs import contextdoc_list_all, contextdoc_read_doc


class CharacterCurateResult(BaseModel):
    """Result structure from character curator subagent."""

    character_id: str = Field(description="Character identifier that was curated.")
    name_tgt: str | None = Field(description="Localized character name in target language.")
    pronouns: str | None = Field(description="Pronoun preferences or notes (e.g., 'she/her', 'they/them').")
    notes: str | None = Field(description="Speech patterns, personality notes, or translation guidance.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant curating character metadata.

Workflow:
1. Read the character's current metadata.
2. Update name_tgt (in the TARGET language), pronouns, or notes as needed for translation quality.
3. If the character is missing, create it with character_create_entry.
4. Use character_delete_entry only if a character is clearly invalid (requires approval).
5. Capture pronouns and notes in the SOURCE language. Call each update tool at most once. End when updates are recorded."""


async def curate_character(
    context: ProjectContext,
    character_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CharacterCurateResult:
    """Run the character curator for *character_id* and return metadata.

    Returns:
        CharacterCurateResult: Updated character metadata.
    """
    logger.info("Curating character %s", character_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_character_curator_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    user_prompt = build_character_curator_user_prompt(context, character_id)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'character-curate'}:{character_id}",
    )

    updated_character = context.get_character(character_id)
    return CharacterCurateResult(
        character_id=character_id,
        name_tgt=updated_character.name_tgt,
        pronouns=updated_character.pronouns,
        notes=updated_character.notes,
    )


def create_character_curator_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create character curator LangChain subagent.

    Returns:
        CompiledStateGraph: Runnable agent graph.
    """
    tools = _build_character_curator_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    interrupt_on = {
        "character_update_name_tgt": True,
        "character_update_pronouns": True,
        "character_update_notes": True,
        "character_delete_entry": True,
    }
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )


def build_character_curator_user_prompt(context: ProjectContext, character_id: str) -> str:
    """Construct the user prompt for the character curator.

    Returns:
        str: User prompt text.
    """
    target_lang = context.game.target_lang.upper()
    source_lang = context.game.source_lang.upper()
    available_ids = ", ".join(sorted(context.characters.keys()))
    return f"""Curate metadata for this character.

Character ID: {character_id}
Target Language: {target_lang}
Source Language: {source_lang}
Available Characters: {available_ids}

Instructions:
1. Read the character's current metadata.
2. Update name_tgt using character_update_name_tgt(character_id, name) in {target_lang} if missing or weak.
3. Update pronouns with character_update_pronouns(character_id, pronouns) and describe in {source_lang}.
4. Update notes with character_update_notes(character_id, notes) in {source_lang}.
5. If character is invalid, you may call character_delete_entry (will require approval).
6. End when updates are complete."""


def _build_character_curator_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Return tools for the character curator subagent bound to the shared context."""
    updated_name_tgt: set[str] = set()
    updated_pronouns: set[str] = set()
    updated_notes: set[str] = set()
    context_doc_tools = _build_context_doc_tools(context)

    @tool("character_read_entry")
    def read_character_tool(character_id: str) -> str:
        """Return current metadata for this character."""
        return character_read_entry(context, character_id)

    @tool("character_create_entry")
    async def add_character_tool(
        character_id: str,
        name_src: str,
        name_tgt: str | None = None,
        pronouns: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Add a new character entry with provenance tracking.

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
        """Update the target language name for this character.

        Returns:
            str: Status message.
        """
        return await character_update_name_tgt(context, character_id, name_tgt, updated_name_tgt=updated_name_tgt)

    @tool("character_update_pronouns")
    async def update_character_pronouns_tool(character_id: str, pronouns: str) -> str:
        """Update pronoun preferences for this character.

        Returns:
            str: Status message.
        """
        return await character_update_pronouns(context, character_id, pronouns, updated_pronouns=updated_pronouns)

    @tool("character_update_notes")
    async def update_character_notes_tool(character_id: str, notes: str) -> str:
        """Update character notes (personality, speech patterns, translation guidance).

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
        *context_doc_tools,
        update_character_name_tgt_tool,
        update_character_pronouns_tool,
        update_character_notes_tool,
        delete_character_tool,
    ]


def _build_context_doc_tools(context: ProjectContext) -> list[BaseTool]:
    """Return context doc tools for subagent use."""

    @tool("contextdoc_list_all")
    async def list_context_docs_tool() -> str:
        """Return the available context document names."""
        return await contextdoc_list_all(context)

    @tool("contextdoc_read_doc")
    async def read_context_doc_tool(filename: str) -> str:
        """Return the contents of a context document."""
        return await contextdoc_read_doc(context, filename)

    return [list_context_docs_tool, read_context_doc_tool]
