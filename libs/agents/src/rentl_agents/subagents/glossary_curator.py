"""Glossary curator subagent.

This subagent proposes new glossary entries or updates to existing entries
with HITL approval for consistent terminology management.
"""

from __future__ import annotations

from deepagents import create_deep_agent
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.tools.glossary import build_glossary_tools


class GlossaryDetailResult(BaseModel):
    """Result structure from glossary curator subagent."""

    entries_added: int = Field(description="Number of new glossary entries added.")
    entries_updated: int = Field(description="Number of existing glossary entries updated.")
    total_entries: int = Field(description="Total number of glossary entries after curation.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant managing glossary entries.

Your task is to curate terminology for consistent translation:

1. **Search**: Look up existing glossary entries by source term
2. **Add**: Propose new glossary entries for important terms that aren't documented
3. **Update**: Refine existing entries with better target translations or notes

**Workflow:**
1. Read context documents to understand the game's terminology
2. Search for key terms that need glossary entries
3. Add new entries for undocumented terms (with target translation and notes)
4. Update existing entries if they need refinement
5. End the conversation once curation is complete

**Important:**
- Focus on terms that need consistent translation (honorifics, character names, locations, cultural terms)
- Provide clear target language renderings and translator guidance in notes
- Be selective - not every word needs a glossary entry
- Respect existing human-authored data (you may be asked for approval before overwriting)
- Each add/update tool can be called multiple times if needed
"""


async def detail_glossary(context: ProjectContext, *, allow_overwrite: bool = False) -> GlossaryDetailResult:
    """Run the glossary curator agent and return curation results.

    Args:
        context: Project context with metadata.
        allow_overwrite: Allow overwriting existing human-authored metadata.

    Returns:
        GlossaryDetailResult: Curation statistics.
    """
    logger.info("Curating glossary")
    initial_count = len(context.glossary)
    tools = build_glossary_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    agent = create_deep_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)

    source_lang = context.game.source_lang.upper()
    target_lang = context.game.target_lang.upper()

    user_prompt = f"""Curate the glossary for this game project.

Source Language: {source_lang}
Target Language: {target_lang}
Current Glossary Entries: {initial_count}

Instructions:
1. Review context documents to understand key terminology
2. Search for existing glossary entries that may need refinement
3. Add new entries for important untranslated terms (honorifics, names, cultural terms)
4. Update existing entries if they need better target translations or notes
5. End conversation when glossary curation is complete

Begin curation now."""

    await agent.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})

    # Calculate statistics
    final_count = len(context.glossary)
    entries_added = final_count - initial_count
    entries_updated = context._glossary_update_count if hasattr(context, "_glossary_update_count") else 0

    result = GlossaryDetailResult(
        entries_added=entries_added,
        entries_updated=entries_updated,
        total_entries=final_count,
    )

    logger.info(
        "Glossary curation complete: %d added, %d updated, %d total",
        result.entries_added,
        result.entries_updated,
        result.total_entries,
    )

    return result
