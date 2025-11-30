"""Style checker subagent."""

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
    get_ui_settings,
    read_style_guide,
    read_translations,
    record_translation_check,
)

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


def create_style_checker_subagent(
    context: ProjectContext, *, checkpointer: BaseCheckpointSaver | None = None
) -> CompiledStateGraph:
    """Create style checker LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for style checks.
    """
    tools = _build_style_checker_tools(context)
    model = get_default_chat_model()
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
    logger.info("Launching style-checker with tools: %s", ", ".join(tool_names))
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return graph


def _build_style_checker_tools(context: ProjectContext) -> list[BaseTool]:
    """Return tools for the style checker subagent bound to the shared context."""

    @tool("read_translations")
    async def read_translations_tool(scene_id: str) -> str:
        """Return translated lines for a scene."""
        return await read_translations(context, scene_id)

    @tool("read_style_guide")
    async def read_style_guide_tool() -> str:
        """Return the project style guide content."""
        return await read_style_guide(context)

    @tool("get_ui_settings")
    def get_ui_settings_tool() -> str:
        """Return UI constraints from game metadata."""
        return get_ui_settings(context)

    @tool("record_style_check")
    async def record_style_check_tool(scene_id: str, line_id: str, passed: bool, note: str | None = None) -> str:
        """Record a style check result for a translated line.

        Returns:
            str: Confirmation message after recording the check.
        """
        return await record_translation_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            check_type="style_check",
            origin="agent:style_checker",
        )

    return [read_translations_tool, read_style_guide_tool, get_ui_settings_tool, record_style_check_tool]


async def run_style_checks(
    context: ProjectContext,
    scene_id: str,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    thread_id: str | None = None,
) -> StyleCheckResult:
    """Run style checker for a scene.

    Returns:
        StyleCheckResult: Recorded style check counts.
    """
    subagent = create_style_checker_subagent(context, checkpointer=checkpointer)
    await subagent.ainvoke(
        {"messages": [{"role": "user", "content": build_style_checker_user_prompt(scene_id)}]},
        config={"configurable": {"thread_id": thread_id or f"edit-style:{scene_id}"}},
    )
    translations = await context.get_translations(scene_id)
    # Count checks recorded for this scene
    recorded = 0
    for line in translations:
        if "style_check" in line.meta.checks:
            recorded += 1

    return StyleCheckResult(scene_id=scene_id, checks_recorded=recorded)


def build_style_checker_user_prompt(scene_id: str) -> str:
    """Construct the user prompt for style checks.

    Returns:
        str: User prompt content to send to the style checker agent.
    """
    return f"Check style for {scene_id}."
