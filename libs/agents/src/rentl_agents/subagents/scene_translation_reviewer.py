"""Translation reviewer subagent."""

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
    styleguide_read_full,
    translation_create_review_check,
    translation_read_scene,
    ui_read_settings,
)

logger = get_logger(__name__)


class TranslationReviewResult(BaseModel):
    """Result for translation reviewer subagent."""

    scene_id: str = Field(description="Scene reviewed")
    checks_recorded: int = Field(description="Number of review checks recorded.")


SYSTEM_PROMPT = """You are a translation reviewer assessing fidelity and fluency.

Workflow:
1) Call translation_read_scene(scene_id) to see translated lines.
2) Evaluate faithfulness to source, tone, and readability.
3) Reference style guide and UI settings when relevant by calling styleguide_read_full and ui_read_settings.
4) Call translation_create_review_check(scene_id, line_id, passed, note) for each line reviewed.
5) Be concise and avoid restating text. End when checks are recorded."""


def create_translation_reviewer_subagent(
    context: ProjectContext, *, checkpointer: BaseCheckpointSaver | None = None
) -> CompiledStateGraph:
    """Create translation reviewer LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for translation review.
    """
    tools = _build_translation_reviewer_tools(context)
    model = get_default_chat_model()
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
    logger.info("Launching translation-reviewer with tools: %s", ", ".join(tool_names))
    graph = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return graph


async def run_translation_review(
    context: ProjectContext,
    scene_id: str,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    thread_id: str | None = None,
) -> TranslationReviewResult:
    """Run translation review for a scene.

    Returns:
        TranslationReviewResult: Recorded review counts.
    """
    subagent = create_translation_reviewer_subagent(context, checkpointer=checkpointer)
    await subagent.ainvoke(
        {"messages": [{"role": "user", "content": build_translation_reviewer_user_prompt(scene_id)}]},
        config={"configurable": {"thread_id": thread_id or f"edit-review:{scene_id}"}},
    )
    translations = await context.get_translations(scene_id)
    recorded = sum(1 for line in translations if "translation_review" in line.meta.checks)
    return TranslationReviewResult(scene_id=scene_id, checks_recorded=recorded)


def build_translation_reviewer_user_prompt(scene_id: str) -> str:
    """Construct the user prompt for translation review.

    Returns:
        str: User prompt content to send to the translation reviewer agent.
    """
    return f"Review translation for {scene_id}."


def _build_translation_reviewer_tools(context: ProjectContext) -> list[BaseTool]:
    """Return tools for the translation reviewer subagent bound to the shared context."""

    @tool("translation_read_scene")
    async def read_translations_tool(scene_id: str) -> str:
        """Return translated lines for a scene."""
        return await translation_read_scene(context, scene_id)

    @tool("styleguide_read_full")
    async def read_style_guide_tool() -> str:
        """Return the project style guide content."""
        return await styleguide_read_full(context)

    @tool("ui_read_settings")
    def get_ui_settings_tool() -> str:
        """Return UI constraints from game metadata."""
        return ui_read_settings(context)

    @tool("translation_create_review_check")
    async def record_translation_review_tool(scene_id: str, line_id: str, passed: bool, note: str | None = None) -> str:
        """Record a translation review result for a translated line.

        Returns:
            str: Confirmation message after recording the check.
        """
        return await translation_create_review_check(
            context,
            scene_id,
            line_id,
            passed,
            note,
            origin="agent:scene_translation_reviewer",
        )

    return [
        read_translations_tool,
        read_style_guide_tool,
        get_ui_settings_tool,
        record_translation_review_tool,
    ]
