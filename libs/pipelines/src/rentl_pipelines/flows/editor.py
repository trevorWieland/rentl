"""Editor pipeline orchestrating QA subagents."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import cast

import anyio
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.backends.coordinator import create_coordinator_agent
from rentl_agents.subagents.consistency_checks import create_consistency_checker_subagent
from rentl_agents.subagents.style_checks import create_style_checker_subagent
from rentl_agents.subagents.translation_reviewer import create_translation_reviewer_subagent
from rentl_agents.tools.stats import build_stats_tools
from rentl_core.context.project import load_project_context
from rentl_core.util.logging import get_logger

from rentl_pipelines.flows.utils import SupportsAinvoke, invoke_with_interrupts

logger = get_logger(__name__)

_EDITOR_SYSTEM_PROMPT = """You are the Editor/QA coordinator.

Use task() to run QA subagents (style, consistency, translation review) on translated scenes.
Process every translated scene unless instructed otherwise. Use progress tools when helpful and stop when complete."""


class EditorResult(BaseModel):
    """Results from the Editor pipeline."""

    scenes_checked: int = Field(description="Number of scenes QA'd.")


async def _run_editor_async(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    decision_handler: Callable[[list[str]], list[str]] | None = None,
    thread_id: str | None = None,
) -> EditorResult:
    """Run the Editor pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to QA.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.

    Returns:
        EditorResult: QA summary for the run.
    """
    logger.info("Starting Editor pipeline for %s", project_path)
    context = await load_project_context(project_path)

    target_scene_ids = scene_ids if scene_ids else sorted(context.scenes.keys())
    if not target_scene_ids:
        return EditorResult(scenes_checked=0)

    subagents = [
        create_style_checker_subagent(context),
        create_consistency_checker_subagent(context),
        create_translation_reviewer_subagent(context),
    ]

    tools = build_stats_tools(context)
    model = get_default_chat_model()
    tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
    subagent_names = [subagent["name"] for subagent in subagents]
    logger.info("Editor coordinator starting with subagents: %s", ", ".join(subagent_names))
    logger.info("Editor progress tools: %s", ", ".join(tool_names))

    agent = create_coordinator_agent(
        model=model,
        tools=tools,
        subagents=subagents,
        system_prompt=_EDITOR_SYSTEM_PROMPT,
        interrupt_on={
            "record_style_check": True,
            "record_consistency_check": True,
            "record_translation_review": True,
        },
        checkpointer=MemorySaver(),
    )

    user_prompt = (
        "Run QA on translated scenes.\n"
        "Use task() to run the QA subagents for each scene.\n"
        f"Scenes: {', '.join(target_scene_ids)}\n"
        "Use get_translation_progress as needed. End when QA is complete."
    )

    await invoke_with_interrupts(
        cast(SupportsAinvoke, agent),
        {"messages": [{"role": "user", "content": user_prompt}]},
        decision_handler=decision_handler,
        thread_id=thread_id,
    )

    result = EditorResult(scenes_checked=len(target_scene_ids))
    logger.info("Editor pipeline complete: %s", result)
    return result


def run_editor(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    decision_handler: Callable[[list[str]], list[str]] | None = None,
    thread_id: str | None = None,
) -> EditorResult:
    """Run the Editor pipeline.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to QA.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.

    Returns:
        EditorResult: QA summary for the run.
    """
    return anyio.run(
        partial(
            _run_editor_async,
            project_path,
            scene_ids=scene_ids,
            decision_handler=decision_handler,
            thread_id=thread_id,
        )
    )
