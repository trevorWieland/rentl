"""Character detailer subagent.

This subagent enriches character metadata with bios, pronouns, and speech pattern notes
by analyzing scenes where characters appear.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.hitl.checkpoints import get_default_checkpointer
from rentl_agents.hitl.invoke import Decision, run_with_human_loop
from rentl_agents.tools.character import build_character_tools


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
3. **Notes**: Capture personality traits, speech patterns, tone, or translation guidance

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

    target_lang = context.game.target_lang.upper()

    user_prompt = f"""Enrich metadata for this character.

Character ID: {character_id}
Target Language: {target_lang}

Instructions:
1. Read the character's current metadata
2. Review any context documents that mention this character
3. Update name_tgt with appropriate localized name (if empty or needs refinement) using update_character_name_tgt(character_id, name)
4. Update pronouns with pronoun preferences (e.g., "she/her", "he/him", "they/them") using update_character_pronouns(character_id, pronouns)
5. Update notes with personality, speech patterns, tone, translation guidance using update_character_notes(character_id, notes)
6. End conversation when all updates are complete

Begin analysis now."""

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
    tools = build_character_tools(context, allow_overwrite=allow_overwrite)
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
