"""Location curator subagent (global metadata)."""

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
    location_delete_entry,
    location_read_entry,
    location_update_description,
    location_update_name_tgt,
)


class LocationCurateResult(BaseModel):
    """Result structure from location curator subagent."""

    location_id: str = Field(description="Location identifier that was curated.")
    name_tgt: str | None = Field(description="Localized location name in target language.")
    description: str | None = Field(description="Location description with mood cues and atmospheric details.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant curating location metadata. Write descriptions in the source language and localized names in the target language.

Workflow:
1. Read the location's current metadata.
2. Update name_tgt and description as needed for translation quality.
3. If the location is missing, create it with location_create_entry.
4. Use location_delete_entry only if a location is clearly invalid (requires approval).
5. Call each update tool at most once. End when updates are recorded."""


async def curate_location(
    context: ProjectContext,
    location_id: str,
    *,
    allow_overwrite: bool = False,
    decision_handler: Callable[[list[str]], list[Decision]] | None = None,
    thread_id: str | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> LocationCurateResult:
    """Run the location curator for *location_id* and return metadata.

    Returns:
        LocationCurateResult: Updated location metadata.
    """
    logger.info("Curating location %s", location_id)
    effective_checkpointer: BaseCheckpointSaver = checkpointer or await get_default_checkpointer()
    subagent = create_location_curator_subagent(
        context, allow_overwrite=allow_overwrite, checkpointer=effective_checkpointer
    )

    user_prompt = build_location_curator_user_prompt(context, location_id)
    await run_with_human_loop(
        subagent,
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=f"{thread_id or 'location-curate'}:{location_id}",
    )

    updated_location = context.get_location(location_id)
    return LocationCurateResult(
        location_id=location_id,
        name_tgt=updated_location.name_tgt,
        description=updated_location.description,
    )


def create_location_curator_subagent(
    context: ProjectContext,
    *,
    allow_overwrite: bool = False,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """Create location curator LangChain subagent.

    Returns:
        CompiledStateGraph: Runnable agent graph.
    """
    tools = _build_location_curator_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    interrupt_on = {
        "location_update_name_tgt": True,
        "location_update_description": True,
        "location_delete_entry": True,
    }
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on=interrupt_on)],
        checkpointer=checkpointer,
    )


def build_location_curator_user_prompt(context: ProjectContext, location_id: str) -> str:
    """Construct the user prompt for the location curator.

    Returns:
        str: User prompt text.
    """
    target_lang = context.game.target_lang.upper()
    source_lang = context.game.source_lang.upper()
    available_locations = ", ".join(sorted(context.locations.keys()))
    return f"""Curate metadata for this location.

Location ID: {location_id}
Target Language: {target_lang}
Source Language: {source_lang}
Available Locations: {available_locations}

Instructions:
1. Read the location's current metadata.
2. Update name_tgt using location_update_name_tgt(location_id, name) in {target_lang} if missing or weak.
3. Update description using location_update_description(location_id, description) in {source_lang}.
4. If location is invalid, you may call location_delete_entry (will require approval).
5. End when updates are complete."""


def _build_location_curator_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Return tools for the location curator subagent bound to the shared context."""
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
            str: Status message.
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
            str: Status message.
        """
        return await location_update_name_tgt(context, location_id, name_tgt, updated_name_tgt=updated_name_tgt)

    @tool("location_update_description")
    async def update_location_description_tool(location_id: str, description: str) -> str:
        """Update the description for this location.

        Returns:
            str: Status message.
        """
        return await location_update_description(
            context, location_id, description, updated_description=updated_description
        )

    @tool("location_delete_entry")
    async def delete_location_tool(location_id: str) -> str:
        """Delete a location entry.

        Returns:
            str: Status message.
        """
        return await location_delete_entry(context, location_id)

    return [
        read_location_tool,
        add_location_tool,
        *context_doc_tools,
        update_location_name_tgt_tool,
        update_location_description_tool,
        delete_location_tool,
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
