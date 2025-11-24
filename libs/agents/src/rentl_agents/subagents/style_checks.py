"""Style checker subagent."""

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
from rentl_agents.tools.qa import get_ui_settings, read_style_guide, read_translations, record_style_check

logger = get_logger(__name__)


class StyleCheckResult(BaseModel):
    """Result for style checker subagent."""

    scene_id: str = Field(description="Scene reviewed")
    checks_recorded: int = Field(description="Number of style checks recorded.")


SYSTEM_PROMPT = """You are a style checker enforcing VN formatting.

Workflow:
1) Call read_translations(scene_id) to see translated lines.
2) Call read_style_guide and get_ui_settings to understand style constraints (line length, honorifics, etc.).
3) For each line, decide pass/fail for style. Use max line length from UI settings; defer to style guide for tone choices.
4) Call record_style_check(scene_id, line_id, passed, note) for each line you review.
5) Be concise and avoid restating the text. End when checks are recorded."""


def create_style_checker_subagent(context: ProjectContext, *, name: str | None = None) -> CompiledSubAgent:
    """Create style checker LangChain subagent.

    Returns:
        CompiledSubAgent: Configured style checker agent.
    """
    tools = [read_translations, read_style_guide, get_ui_settings, record_style_check]
    model = get_default_chat_model()
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        context_schema=AgentContext,
        middleware=[cast(AgentMiddleware[AgentState, AgentContext], ContextInjectionMiddleware(context))],  # type: ignore[arg-type]
    )

    return CompiledSubAgent(
        name=name or "style-checker",
        description="Runs style checks on translated lines",
        runnable=graph,
    )


async def run_style_checks(context: ProjectContext, scene_id: str) -> StyleCheckResult:
    """Run style checker for a scene.

    Returns:
        StyleCheckResult: Recorded style check counts.
    """
    subagent = create_style_checker_subagent(context)
    await subagent["runnable"].ainvoke({"messages": [{"role": "user", "content": f"Check style for {scene_id}."}]})
    translations = await context.get_translations(scene_id)
    # Count checks recorded for this scene
    recorded = 0
    for line in translations:
        if "style_check" in line.meta.checks:
            recorded += 1

    return StyleCheckResult(scene_id=scene_id, checks_recorded=recorded)
