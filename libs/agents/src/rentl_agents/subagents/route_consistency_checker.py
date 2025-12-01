"""Route-level consistency checker subagent."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.tools import BaseTool, tool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.tools.qa import (
    translation_create_consistency_check,
    translation_read_scene,
)

logger = get_logger(__name__)


class RouteConsistencyCheckResult(BaseModel):
    """Result for route consistency checker subagent."""

    scene_id: str = Field(description="Scene reviewed")
    checks_recorded: int = Field(description="Number of consistency checks recorded.")


SYSTEM_PROMPT = """You are a consistency checker ensuring terminology and pronouns match glossary/metadata.

Workflow:
1) Call translation_read_scene(scene_id) to see translated lines.
2) Verify character names/pronouns and glossary terms are consistent.
3) Call translation_create_consistency_check(scene_id, line_id, passed, note) for each line reviewed.
4) Be concise and avoid restating text. End when checks are recorded."""


def create_route_consistency_checker_subagent(
    context: ProjectContext, *, checkpointer: BaseCheckpointSaver | None = None
) -> CompiledStateGraph:
    """Create route consistency checker LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for consistency checks.
    """
    tools = _build_route_consistency_checker_tools(context)
    model = get_default_chat_model()
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
    logger.info("Launching route-consistency-checker with tools: %s", ", ".join(tool_names))
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return graph


def _build_route_consistency_checker_tools(context: ProjectContext) -> list[BaseTool]:
    """Return tools for the route consistency checker subagent bound to the shared context."""

    @tool("translation_read_scene")
    async def read_translations_tool(scene_id: str) -> str:
        """Return translated lines for a scene."""
        return await translation_read_scene(context, scene_id)

    @tool("translation_create_consistency_check")
    async def record_consistency_check_tool(scene_id: str, line_id: str, passed: bool, note: str | None = None) -> str:
        """Record a consistency check result for a translated line.

        Returns:
            str: Confirmation message after recording the check.
        """
        return await translation_create_consistency_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            origin="agent:route_consistency_checker",
        )

    return [read_translations_tool, record_consistency_check_tool]


async def run_route_consistency_checks(
    context: ProjectContext,
    scene_id: str,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    thread_id: str | None = None,
) -> RouteConsistencyCheckResult:
    """Run consistency checker for a scene.

    Returns:
        RouteConsistencyCheckResult: Recorded consistency check counts.
    """
    subagent = create_route_consistency_checker_subagent(context, checkpointer=checkpointer)
    await subagent.ainvoke(
        {"messages": [{"role": "user", "content": build_route_consistency_checker_user_prompt(scene_id)}]},
        config={"configurable": {"thread_id": thread_id or f"edit-consistency:{scene_id}"}},
    )
    translations = await context.get_translations(scene_id)
    recorded = sum(1 for line in translations if "consistency_check" in line.meta.checks)
    return RouteConsistencyCheckResult(scene_id=scene_id, checks_recorded=recorded)


def build_route_consistency_checker_user_prompt(scene_id: str) -> str:
    """Construct the user prompt for consistency checks.

    Returns:
        str: User prompt content to send to the consistency checker agent.
    """
    return f"Check consistency for {scene_id}."
