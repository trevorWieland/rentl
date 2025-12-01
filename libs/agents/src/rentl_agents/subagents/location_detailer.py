"""Location detailer subagent.

This subagent enriches location metadata with descriptions, mood cues, and atmospheric details
by analyzing scenes set in those locations.
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
from rentl_agents.tools.context_docs import contextdoc_list_all, contextdoc_read_doc
from rentl_agents.tools.location import (
    location_create_entry,
    location_read_entry,
    location_update_description,
    location_update_name_tgt,
)


class LocationDetailResult(BaseModel):
    """Result structure from location detailer subagent."""

    location_id: str = Field(description="Location identifier that was detailed.")
    name_tgt: str | None = Field(description="Localized location name in target language.")
    description: str | None = Field(description="Location description with mood cues and atmospheric details.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant enriching location metadata.

Your task is to analyze location information and enhance their metadata for translation quality:

1. **Target Name**: Provide or refine the localized name in the target language
2. **Description**: Capture the location's appearance, mood, atmosphere, and contextual details (write descriptions in the source language)

**Workflow:**
1. Read the location's current metadata
2. Read relevant context documents if available
3. Update the target name if needed (or propose one if empty)
4. Update description with vivid, useful details (physical appearance, lighting, mood, atmosphere)
5. End the conversation once metadata is updated

**Important:**
- Focus on information useful for translators and consistent scene setting
- Capture atmosphere, mood, time of day, weather, architectural details, ambient sounds
- Be concise but evocative
- Respect existing human-authored data (you may be asked for approval before overwriting)
- Each update tool should only be called once per session
"""


async def detail_location(
    context: ProjectContext,
    location_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> LocationDetailResult:
    """Run the location detailer agent for *location_id* and return metadata.

    Args:
        context: Project context with metadata.
        location_id: Location identifier to detail.
        allow_overwrite: Allow overwriting existing human-authored metadata.
        decision_handler: Optional callback to resolve HITL interrupts.
        thread_id: Optional thread identifier for resumable runs.
        checkpointer: Optional LangGraph checkpointer (defaults to SQLite if configured).

    Returns:
        LocationDetailResult: Updated location metadata.
    """
    logger.info("Detailing location %s", location_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_location_detailer_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    user_prompt = build_location_detailer_user_prompt(context, location_id)

    logger.debug("Location detailer prompt for %s:\n%s", location_id, user_prompt)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'location-detail'}:{location_id}",
    )

    # Retrieve updated location metadata
    updated_location = context.get_location(location_id)

    result = LocationDetailResult(
        location_id=location_id,
        name_tgt=updated_location.name_tgt,
        description=updated_location.description,
    )

    logger.info(
        "Location %s metadata: name_tgt=%s, description=%d chars",
        location_id,
        result.name_tgt or "(empty)",
        len(result.description) if result.description else 0,
    )

    return result


def create_location_detailer_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create location detailer LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for location detailing.
    """
    tools = _build_location_detailer_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    interrupt_on = {
        "location_update_name_tgt": True,
        "location_update_description": True,
    }
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )

    return graph


def build_location_detailer_user_prompt(context: ProjectContext, location_id: str) -> str:
    """Construct the user prompt for the location detailer.

    Returns:
        str: User prompt content to send to the location detailer agent.
    """
    target_lang = context.game.target_lang.upper()
    source_lang = context.game.source_lang.upper()
    available_locations = ", ".join(sorted(context.locations.keys()))
    return f"""Enrich metadata for this location.

Location ID: {location_id}
Target Language: {target_lang}
Source Language: {source_lang}
Available Locations: {available_locations}

Instructions:
1. Read the location's current metadata
2. Review any context documents that mention this location
3. Update name_tgt with appropriate localized name (if empty or needs refinement) using location_update_name_tgt(location_id, name) in {target_lang}
4. Update description with vivid details (appearance, mood, atmosphere, sensory details) using location_update_description(location_id, description) in the source language
5. End conversation when all updates are complete

Begin analysis now."""


def _build_location_detailer_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Return tools for the location detailer subagent bound to the shared context."""
    updated_name_tgt: set[str] = set()
    updated_description: set[str] = set()
    context_doc_tools = _build_context_doc_tools(context)

    @tool("location_read_entry")
    def read_location_tool(location_id: str) -> str:
        """Return current metadata for this location."""
        return location_read_entry(context, location_id)

    @tool("location_create_entry")
    async def add_location_tool(
        location_id: str,
        name_src: str,
        name_tgt: str | None = None,
        description: str | None = None,
    ) -> str:
        """Add a new location entry with provenance tracking.

        Returns:
            str: Status message after attempting creation.
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
        """Update the target language name for this location.

        Returns:
            str: Confirmation message after persistence.
        """
        return await location_update_name_tgt(context, location_id, name_tgt, updated_name_tgt=updated_name_tgt)

    @tool("location_update_description")
    async def update_location_description_tool(location_id: str, description: str) -> str:
        """Update the description for this location.

        Returns:
            str: Confirmation message after persistence.
        """
        return await location_update_description(
            context, location_id, description, updated_description=updated_description
        )

    return [
        read_location_tool,
        add_location_tool,
        *context_doc_tools,
        update_location_name_tgt_tool,
        update_location_description_tool,
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
