"""Location detailer subagent.

This subagent enriches location metadata with descriptions, mood cues, and atmospheric details
by analyzing scenes set in those locations.
"""

from __future__ import annotations

from typing import cast

from deepagents import CompiledSubAgent
from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import AgentMiddleware
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.middleware.context import AgentContext, ContextInjectionMiddleware
from rentl_agents.tools.location import build_location_tools


class LocationDetailResult(BaseModel):
    """Result structure from location detailer subagent."""

    location_id: str = Field(description="Location identifier that was detailed.")
    name_tgt: str | None = Field(description="Localized location name in target language.")
    description: str | None = Field(description="Location description with mood cues and atmospheric details.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant enriching location metadata.

Your task is to analyze location information and enhance their metadata for translation quality:

1. **Target Name**: Provide or refine the localized name in the target language
2. **Description**: Capture the location's appearance, mood, atmosphere, and contextual details

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
    context: ProjectContext, location_id: str, *, allow_overwrite: bool = False
) -> LocationDetailResult:
    """Run the location detailer agent for *location_id* and return metadata.

    Args:
        context: Project context with metadata.
        location_id: Location identifier to detail.
        allow_overwrite: Allow overwriting existing human-authored metadata.

    Returns:
        LocationDetailResult: Updated location metadata.
    """
    logger.info("Detailing location %s", location_id)
    subagent = create_location_detailer_subagent(context, allow_overwrite=allow_overwrite)
    runnable = subagent["runnable"]

    target_lang = context.game.target_lang.upper()

    user_prompt = f"""Enrich metadata for this location.

Location ID: {location_id}
Target Language: {target_lang}

Instructions:
1. Read the location's current metadata
2. Review any context documents that mention this location
3. Update name_tgt with appropriate localized name (if empty or needs refinement) using update_location_name_tgt(location_id, name)
4. Update description with vivid details (appearance, mood, atmosphere, sensory details) using update_location_description(location_id, description)
5. End conversation when all updates are complete

Begin analysis now."""

    await runnable.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})

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
    name: str | None = None,
) -> CompiledSubAgent:
    """Create location detailer LangChain subagent.

    Returns:
        CompiledSubAgent: Configured location detailer agent.
    """
    tools = build_location_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        context_schema=AgentContext,
        # ty lacks support for AgentMiddleware generic narrowing; ignore is safe here.
        middleware=[cast(AgentMiddleware[AgentState, AgentContext], ContextInjectionMiddleware(context))],  # type: ignore[arg-type]
    )

    return CompiledSubAgent(
        name=name or "location-detailer",
        description="Enriches location metadata with localized names and descriptions",
        runnable=graph,
    )
