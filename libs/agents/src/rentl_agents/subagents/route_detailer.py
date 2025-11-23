"""Route detailer subagent.

This subagent enriches route metadata with synopsis and primary character identification
by analyzing the scenes that make up each route.
"""

from __future__ import annotations

from deepagents import create_deep_agent
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.tools.route import build_route_tools


class RouteDetailResult(BaseModel):
    """Result structure from route detailer subagent."""

    route_id: str = Field(description="Route identifier that was detailed.")
    synopsis: str | None = Field(description="Synopsis or description of the route.")
    primary_characters: list[str] = Field(description="Key characters associated with the route.")


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a localization assistant enriching route metadata.

Your task is to analyze route information and enhance their metadata for translation quality:

1. **Synopsis**: Provide or refine a concise route synopsis (1-3 sentences covering narrative arc)
2. **Primary Characters**: Identify key characters featured in this route

**Workflow:**
1. Read the route's current metadata (including scene list)
2. Read relevant context documents if available
3. Update synopsis with a concise narrative summary of the route
4. Update primary_characters with character IDs of key characters in this route
5. End the conversation once metadata is updated

**Important:**
- Focus on narrative arc, key plot points, and character relationships
- Keep synopsis concise but informative (1-3 sentences)
- List only primary characters (not every character who appears)
- Respect existing human-authored data (you may be asked for approval before overwriting)
- Each update tool should only be called once per session
"""


async def detail_route(context: ProjectContext, route_id: str, *, allow_overwrite: bool = False) -> RouteDetailResult:
    """Run the route detailer agent for *route_id* and return metadata.

    Args:
        context: Project context with metadata.
        route_id: Route identifier to detail.
        allow_overwrite: Allow overwriting existing human-authored metadata.

    Returns:
        RouteDetailResult: Updated route metadata.
    """
    logger.info("Detailing route %s", route_id)
    tools = build_route_tools(context, route_id, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    agent = create_deep_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)

    user_prompt = f"""Enrich metadata for this route.

Route ID: {route_id}

Instructions:
1. Read the route's current metadata (including scene list)
2. Review any context documents that mention this route
3. Update synopsis with a concise narrative summary (1-3 sentences covering the route's arc)
4. Update primary_characters with key character IDs featured in this route
5. End conversation when all updates are complete

Begin analysis now."""

    await agent.ainvoke({"messages": [{"role": "user", "content": user_prompt}]})

    # Retrieve updated route metadata
    updated_route = context.get_route(route_id)

    result = RouteDetailResult(
        route_id=route_id,
        synopsis=updated_route.synopsis,
        primary_characters=updated_route.primary_characters,
    )

    logger.info(
        "Route %s metadata: synopsis=%d chars, primary_characters=%d",
        route_id,
        len(result.synopsis) if result.synopsis else 0,
        len(result.primary_characters),
    )

    return result
