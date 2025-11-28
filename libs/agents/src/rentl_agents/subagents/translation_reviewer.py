"""Translation reviewer subagent."""

from __future__ import annotations

from langchain.agents import create_agent
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.tools.qa import get_ui_settings, read_style_guide, read_translations, record_translation_review

logger = get_logger(__name__)


class TranslationReviewResult(BaseModel):
    """Result for translation reviewer subagent."""

    scene_id: str = Field(description="Scene reviewed")
    checks_recorded: int = Field(description="Number of review checks recorded.")


SYSTEM_PROMPT = """You are a translation reviewer assessing fidelity and fluency.

Workflow:
1) Call read_translations(scene_id) to see translated lines.
2) Evaluate faithfulness to source, tone, and readability.
3) Reference style guide and UI settings when relevant by calling read_style_guide and get_ui_settings.
4) Call record_translation_review(scene_id, line_id, passed, note) for each line reviewed.
5) Be concise and avoid restating text. End when checks are recorded."""


def create_translation_reviewer_subagent(
    context: ProjectContext, *, checkpointer: BaseCheckpointSaver | None = None
) -> CompiledStateGraph:
    """Create translation reviewer LangChain subagent and return the runnable graph.

    Returns:
        CompiledStateGraph: Runnable agent graph for translation review.
    """
    tools = [read_translations, read_style_guide, get_ui_settings, record_translation_review]
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
        {"messages": [{"role": "user", "content": f"Review translation for {scene_id}."}]},
        config={"configurable": {"thread_id": thread_id or f"edit-review:{scene_id}"}},
    )
    translations = await context.get_translations(scene_id)
    recorded = sum(1 for line in translations if "translation_review" in line.meta.checks)
    return TranslationReviewResult(scene_id=scene_id, checks_recorded=recorded)
