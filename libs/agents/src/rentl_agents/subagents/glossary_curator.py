"""Glossary curator subagent.

This subagent proposes new glossary entries or updates to existing entries
with HITL approval for consistent terminology management.
"""

from __future__ import annotations

from deepagents import CompiledSubAgent
from langchain.agents import create_agent
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

Your task is to curate terminology for consistent translation.

**Workflow:**
1. Call `list_context_docs()` to see available context documents
2. Call `read_context_doc(filename)` to review each document for terminology
3. Call `search_glossary(term)` to check for existing entries
4. Call `add_glossary_entry(term_src, term_tgt, notes)` for new important terms
5. Call `update_glossary_entry(term_src, term_tgt, notes)` to refine existing entries
6. End the conversation once curation is complete

**Important:**
- Focus on terms needing consistent translation (honorifics, character names, locations, cultural terms)
- Provide clear target language renderings and translator guidance in notes
- Be selective - not every word needs a glossary entry
- Respect existing human-authored data (you may be asked for approval before overwriting)
"""


def create_glossary_curator_subagent(context: ProjectContext, *, allow_overwrite: bool = False) -> CompiledSubAgent:
    """Create glossary curator subagent for terminology management.

    Args:
        context: Project context with metadata (shared instance).
        allow_overwrite: Allow overwriting existing human-authored metadata.

    Returns:
        CompiledSubAgent: Glossary curator subagent ready for top-level agent use.
    """
    tools = build_glossary_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()

    # Create LangChain agent (NOT DeepAgent)
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    # Wrap as CompiledSubAgent for DeepAgent use
    return CompiledSubAgent(
        name="glossary-curator",
        description="Curates glossary entries for consistent translation terminology",
        runnable=graph,
    )


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

    # Create the subagent
    subagent = create_glossary_curator_subagent(context, allow_overwrite=allow_overwrite)

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

    # Invoke the subagent directly (for flow usage)
    runnable = subagent["runnable"]
    logger.debug("Glossary curator prompt:\n%s", user_prompt)
    await runnable.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})

    # Calculate statistics
    final_count = len(context.glossary)
    entries_added = final_count - initial_count
    entries_updated = context._glossary_update_count

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
