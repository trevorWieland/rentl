"""Consistency checker subagent."""

from __future__ import annotations

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.tools.qa import read_translations, record_consistency_check

logger = get_logger(__name__)


class ConsistencyCheckResult(BaseModel):
    """Result for consistency checker subagent."""

    scene_id: str = Field(description="Scene reviewed")
    checks_recorded: int = Field(description="Number of consistency checks recorded.")


SYSTEM_PROMPT = """You are a consistency checker ensuring terminology and pronouns match glossary/metadata.

Workflow:
1) Call read_translations(scene_id) to see translated lines.
2) Verify character names/pronouns and glossary terms are consistent.
3) Call record_consistency_check(scene_id, line_id, passed, note) for each line reviewed.
4) Be concise and avoid restating text. End when checks are recorded."""


def create_consistency_checker_subagent(context: ProjectContext) -> CompiledStateGraph:
    """Create consistency checker LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for consistency checks.
    """
    tools = [read_translations, record_consistency_check]
    model = get_default_chat_model()
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
    logger.info("Launching consistency-checker with tools: %s", ", ".join(tool_names))
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    return graph


async def run_consistency_checks(context: ProjectContext, scene_id: str) -> ConsistencyCheckResult:
    """Run consistency checker for a scene.

    Returns:
        ConsistencyCheckResult: Recorded consistency check counts.
    """
    subagent = create_consistency_checker_subagent(context)
    await subagent.ainvoke({"messages": [{"role": "user", "content": f"Check consistency for {scene_id}."}]})
    translations = await context.get_translations(scene_id)
    recorded = sum(1 for line in translations if "consistency_check" in line.meta.checks)
    return ConsistencyCheckResult(scene_id=scene_id, checks_recorded=recorded)
