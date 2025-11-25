"""Editor pipeline orchestrating QA subagents."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import partial
from pathlib import Path
from typing import Literal

import anyio
from pydantic import BaseModel, Field
from rentl_agents.subagents.consistency_checks import run_consistency_checks
from rentl_agents.subagents.style_checks import run_style_checks
from rentl_agents.subagents.translation_reviewer import run_translation_review
from rentl_core.context.project import load_project_context
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


class EditorResult(BaseModel):
    """Results from the Editor pipeline."""

    scenes_checked: int = Field(description="Number of scenes QA'd.")


async def _run_editor_async(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
) -> EditorResult:
    """Run the Editor pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to QA.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent QA runs.
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

    _ = (decision_handler, thread_id)
    semaphore = anyio.Semaphore(max(1, concurrency))

    async def _bounded(coro: Awaitable[object]) -> None:
        async with semaphore:
            await coro

    async with anyio.create_task_group() as tg:
        for sid in target_scene_ids:
            tg.start_soon(_bounded, run_style_checks(context, sid))

    async with anyio.create_task_group() as tg:
        for sid in target_scene_ids:
            tg.start_soon(_bounded, run_consistency_checks(context, sid))

    async with anyio.create_task_group() as tg:
        for sid in target_scene_ids:
            tg.start_soon(_bounded, run_translation_review(context, sid))

    result = EditorResult(scenes_checked=len(target_scene_ids))
    logger.info("Editor pipeline complete: %s", result)
    return result


def run_editor(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
) -> EditorResult:
    """Run the Editor pipeline.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to QA.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent QA runs.
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
            mode=mode,
            concurrency=concurrency,
            decision_handler=decision_handler,
            thread_id=thread_id,
        )
    )
