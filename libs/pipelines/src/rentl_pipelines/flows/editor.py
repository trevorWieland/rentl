"""Editor pipeline orchestrating QA subagents."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import partial
from pathlib import Path
from typing import Literal, TypeVar

import anyio
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field
from rentl_agents.hitl.checkpoints import get_default_checkpointer
from rentl_agents.subagents.consistency_checks import (
    ConsistencyCheckResult,
    run_consistency_checks,
)
from rentl_agents.subagents.style_checks import StyleCheckResult, run_style_checks
from rentl_agents.subagents.translation_reviewer import (
    TranslationReviewResult,
    run_translation_review,
)
from rentl_core.context.project import load_project_context
from rentl_core.util.logging import get_logger

from rentl_pipelines.flows.utils import (
    PIPELINE_FAILURE_EXCEPTIONS,
    PipelineError,
    run_with_retries,
)

logger = get_logger(__name__)
REPORT_FILENAME = "editor_report.json"


class EditorResult(BaseModel):
    """Results from the Editor pipeline."""

    scenes_checked: int = Field(description="Number of scenes QA'd.")
    errors: list[PipelineError] = Field(default_factory=list, description="Errors encountered during QA.")


_T = TypeVar("_T")


async def _run_editor_async(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
    progress_cb: Callable[[str, str], None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    report_path: Path | None = None,
    style_runner: Callable[..., Awaitable[StyleCheckResult]] | None = None,
    consistency_runner: Callable[..., Awaitable[ConsistencyCheckResult]] | None = None,
    review_runner: Callable[..., Awaitable[TranslationReviewResult]] | None = None,
) -> EditorResult:
    """Run the Editor pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to QA.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent QA runs.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.
        progress_cb: Optional callback invoked as (event, scene_id) per QA stage start.
        checkpointer: Optional LangGraph checkpoint saver to reuse (defaults to SQLite).
        report_path: Optional override path for the QA report JSON file.
        style_runner: Optional override for style check runner (for testing).
        consistency_runner: Optional override for consistency check runner (for testing).
        review_runner: Optional override for translation review runner (for testing).

    Returns:
        EditorResult: QA summary for the run.
    """
    logger.info("Starting Editor pipeline for %s", project_path)
    context = await load_project_context(project_path)
    effective_checkpointer = checkpointer or await get_default_checkpointer(project_path / ".rentl" / "checkpoints.db")
    output_reports_dir = project_path / "output" / "reports"
    if report_path is None:
        report_path = output_reports_dir / REPORT_FILENAME

    target_scene_ids = scene_ids if scene_ids else sorted(context.scenes.keys())
    if not target_scene_ids:
        return EditorResult(scenes_checked=0)

    _ = (decision_handler, thread_id)
    semaphore = anyio.Semaphore(max(1, concurrency))
    errors: list[PipelineError] = []
    completed_scene_ids: list[str] = []
    base_thread = thread_id or "edit"
    style_runner = style_runner or run_style_checks
    consistency_runner = consistency_runner or run_consistency_checks
    review_runner = review_runner or run_translation_review

    def _record_error(stage: str, entity_id: str, exc: BaseException) -> None:
        errors.append(PipelineError(stage=stage, entity_id=entity_id, error=str(exc)))
        logger.error("%s failed for %s: %s", stage, entity_id, exc)
        if progress_cb:
            progress_cb(f"{stage}_error", entity_id)

    async def _bounded(stage: str, scene_id: str, coro_factory: Callable[[], Awaitable[_T]]) -> None:
        async with semaphore:
            try:
                await run_with_retries(
                    coro_factory,
                    on_retry=lambda attempt, exc: logger.warning(
                        "Retrying %s for %s (attempt %d): %s", stage, scene_id, attempt + 1, exc
                    ),
                )
                completed_scene_ids.append(scene_id)
                if progress_cb:
                    progress_cb(f"{stage}_done", scene_id)
            except PIPELINE_FAILURE_EXCEPTIONS as exc:
                _record_error(stage, scene_id, exc)

    async with anyio.create_task_group() as tg:
        for sid in target_scene_ids:
            if progress_cb:
                progress_cb("edit_style_start", sid)
            tg.start_soon(
                _bounded,
                "edit_style",
                sid,
                lambda sid=sid: style_runner(
                    context, sid, checkpointer=effective_checkpointer, thread_id=f"{base_thread}:style:{sid}"
                ),
            )

    async with anyio.create_task_group() as tg:
        for sid in target_scene_ids:
            if progress_cb:
                progress_cb("edit_consistency_start", sid)
            tg.start_soon(
                _bounded,
                "edit_consistency",
                sid,
                lambda sid=sid: consistency_runner(
                    context, sid, checkpointer=effective_checkpointer, thread_id=f"{base_thread}:consistency:{sid}"
                ),
            )

    async with anyio.create_task_group() as tg:
        for sid in target_scene_ids:
            if progress_cb:
                progress_cb("edit_review_start", sid)
            tg.start_soon(
                _bounded,
                "edit_review",
                sid,
                lambda sid=sid: review_runner(
                    context, sid, checkpointer=effective_checkpointer, thread_id=f"{base_thread}:review:{sid}"
                ),
            )

    result = EditorResult(scenes_checked=len(set(completed_scene_ids)), errors=errors)
    await _write_editor_report(report_path, result)
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
    progress_cb: Callable[[str, str], None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    report_path: Path | None = None,
    style_runner: Callable[..., Awaitable[StyleCheckResult]] | None = None,
    consistency_runner: Callable[..., Awaitable[ConsistencyCheckResult]] | None = None,
    review_runner: Callable[..., Awaitable[TranslationReviewResult]] | None = None,
) -> EditorResult:
    """Run the Editor pipeline.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to QA.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent QA runs.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.
        progress_cb: Optional callback invoked as (event, scene_id) per QA stage start.
        checkpointer: Optional LangGraph checkpoint saver to reuse (defaults to SQLite).
        report_path: Optional override path for the QA report JSON file.
        style_runner: Optional override for style check runner (for testing).
        consistency_runner: Optional override for consistency check runner (for testing).
        review_runner: Optional override for translation review runner (for testing).

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
            progress_cb=progress_cb,
            checkpointer=checkpointer,
            report_path=report_path,
            style_runner=style_runner,
            consistency_runner=consistency_runner,
            review_runner=review_runner,
        )
    )


async def _write_editor_report(path: Path, result: EditorResult) -> None:
    """Persist a simple JSON report summarizing editor results."""
    import orjson

    await anyio.Path(path.parent).mkdir(parents=True, exist_ok=True)
    payload = result.model_dump()
    async with await anyio.open_file(path, "wb") as stream:
        await stream.write(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
