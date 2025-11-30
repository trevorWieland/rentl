"""Character detailer subagent.

This subagent enriches character metadata with bios, pronouns, and speech pattern notes
by analyzing scenes where characters appear.
"""

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
    add_character,
    read_character,
    update_character_name_tgt,
    update_character_notes,
    update_character_pronouns,
)
from rentl_agents.tools.context_docs import list_context_docs, read_context_doc


class CharacterDetailResult(BaseModel):
    """Result structure from character detailer subagent."""

    character_id: str = Field(description="Character identifier that was detailed.")
    name_tgt: str | None = Field(description="Localized character name in target language.")
    pronouns: str | None = Field(description="Pronoun preferences or notes (e.g., 'she/her', 'they/them').")
    notes: str | None = Field(
        description="Speech patterns, personality notes, or translation guidance for the character."
    )


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant enriching character metadata.

Your task is to analyze character information and enhance their metadata for translation quality:

1. **Target Name**: Provide or refine the localized name in the target language
2. **Pronouns**: Specify pronoun preferences (e.g., "she/her", "he/him", "they/them")
3. **Notes**: Capture personality traits, speech patterns, tone, or translation guidance (in the source language)

**Workflow:**
1. Read the character's current metadata
2. Read relevant context documents if available
3. Update the target name if needed (or propose one if empty)
4. Update pronouns if needed (or propose them if empty)
5. Update notes with character insights (personality, speech style, tone, quirks)
6. End the conversation once metadata is updated

**Important:**
- Focus on information useful for translators
- Capture speech patterns, formality level, catchphrases, personality traits
- Be concise but informative
- Respect existing human-authored data (you may be asked for approval before overwriting)
- Each update tool should only be called once per session
"""


async def detail_character(
    context: ProjectContext,
    character_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CharacterDetailResult:
    """Run the character detailer agent for *character_id* and return metadata.

    Args:
        context: Project context with metadata.
        character_id: Character identifier to detail.
        allow_overwrite: Allow overwriting existing human-authored metadata.
        decision_handler: Optional callback to resolve HITL interrupts.
        thread_id: Optional thread identifier for resumable runs.
        checkpointer: Optional LangGraph checkpointer (defaults to SQLite if configured).

    Returns:
        CharacterDetailResult: Updated character metadata.
    """
    logger.info("Detailing character %s", character_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_character_detailer_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    user_prompt = build_character_detailer_user_prompt(context, character_id)

    logger.debug("Character detailer prompt for %s:\n%s", character_id, user_prompt)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'character-detail'}:{character_id}",
    )

    # Retrieve updated character metadata
    updated_character = context.get_character(character_id)

    result = CharacterDetailResult(
        character_id=character_id,
        name_tgt=updated_character.name_tgt,
        pronouns=updated_character.pronouns,
        notes=updated_character.notes,
    )

    logger.info(
        "Character %s metadata: name_tgt=%s, pronouns=%s, notes=%d chars",
        character_id,
        result.name_tgt or "(empty)",
        result.pronouns or "(empty)",
        len(result.notes) if result.notes else 0,
    )

    return result


def create_character_detailer_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create character detailer LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for character detailing.
    """
    tools = _build_character_detailer_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    interrupt_on = {
        "update_character_name_tgt": True,
        "update_character_pronouns": True,
        "update_character_notes": True,
    }
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )

    return graph


def build_character_detailer_user_prompt(context: ProjectContext, character_id: str) -> str:
    """Construct the user prompt for the character detailer.

    Returns:
        str: User prompt content to send to the character detailer agent.
    """
    target_lang = context.game.target_lang.upper()
    source_lang = context.game.source_lang.upper()
    available_ids = ", ".join(sorted(context.characters.keys()))
    return f"""Enrich metadata for this character.

Character ID: {character_id}
Target Language: {target_lang}
Source Language: {source_lang}
Available Characters: {available_ids}

Instructions:
1. Read the character's current metadata
2. Review any context documents that mention this character
3. Update name_tgt with appropriate localized name (if empty or needs refinement) using update_character_name_tgt(character_id, name) in {target_lang}
4. Update pronouns with pronoun preferences (e.g., "she/her", "he/him", "they/them") using update_character_pronouns(character_id, pronouns) and describe in {source_lang}
5. Update notes with personality, speech patterns, tone, translation guidance using update_character_notes(character_id, notes) in {source_lang}
6. End conversation when all updates are complete

Begin analysis now."""


def _build_character_detailer_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Return tools for the character detailer subagent bound to the shared context."""
    updated_name_tgt: set[str] = set()
    updated_pronouns: set[str] = set()
    updated_notes: set[str] = set()
    context_doc_tools = _build_context_doc_tools(context)

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


def _build_context_doc_tools(context: ProjectContext) -> list[BaseTool]:
    """Return context doc tools for subagent use."""

    @tool("list_context_docs")
    async def list_context_docs_tool() -> str:
        """Return the available context document names."""
        return await list_context_docs(context)

    @tool("read_context_doc")
    async def read_context_doc_tool(filename: str) -> str:
        """Return the contents of a context document."""
        return await read_context_doc(context, filename)

    return [list_context_docs_tool, read_context_doc_tool]
