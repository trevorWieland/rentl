"""Translator pipeline for scene-by-scene translation.

This pipeline orchestrates the scene translator to produce aligned JP→EN translations
using enriched context from the Context Builder phase.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import partial
from pathlib import Path
from typing import Literal, Protocol, TypeVar

import anyio
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field
from rentl_agents.hitl.checkpoints import get_default_checkpointer, maybe_close_checkpointer
from rentl_agents.subagents.translate_scene import translate_scene
from rentl_core.context.project import load_project_context
from rentl_core.model.line import SourceLine
from rentl_core.util.logging import get_logger

from rentl_pipelines.flows.utils import (
    PIPELINE_FAILURE_EXCEPTIONS,
    PipelineError,
    run_with_retries,
)

logger = get_logger(__name__)


class TranslatorResult(BaseModel):
    """Results from the Translator pipeline."""

    scenes_translated: int = Field(description="Number of scenes translated.")
    lines_translated: int = Field(description="Total number of lines translated.")
    scenes_skipped: int = Field(description="Number of scenes skipped (already translated).")
    errors: list[PipelineError] = Field(default_factory=list, description="Errors encountered during translation.")


_T = TypeVar("_T")


async def _run_translator_async(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    allow_overwrite: bool = False,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
    progress_cb: Callable[[str, str], None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    checkpoint_enabled: bool = True,
) -> TranslatorResult:
    """Run the Translator pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to translate (default: all scenes).
        allow_overwrite: Allow overwriting existing translations.
        mode: Processing mode (overwrite, gap-fill, new-only).
        concurrency: Maximum concurrent scene translations.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.
        progress_cb: Optional callback invoked as (event, scene_id) per scene start.
        checkpointer: Optional LangGraph checkpoint saver to reuse (defaults to SQLite).
        checkpoint_enabled: Disable checkpoint persistence when False (uses in-memory).

    Returns:
        TranslatorResult: Statistics about what was translated.
    """
    logger.info("Starting Translator pipeline for %s", project_path)
    context = await load_project_context(project_path)
    created_checkpointer = checkpointer is None
    effective_checkpointer = (
        checkpointer
        if checkpointer is not None
        else await get_default_checkpointer(project_path / ".rentl" / "checkpoints.db")
        if checkpoint_enabled
        else None
    )

    # Determine which scenes to translate
    target_scene_ids = scene_ids if scene_ids else sorted(context.scenes.keys())
    logger.info("Target scenes: %d", len(target_scene_ids))

    allow_overwrite = mode == "overwrite"
    remaining_scene_ids, scenes_skipped = await _filter_scenes_to_translate(
        context, target_scene_ids, mode, allow_overwrite
    )

    base_thread = thread_id or "translate"

    semaphore = anyio.Semaphore(max(1, concurrency))
    errors: list[PipelineError] = []
    completed_scene_ids: list[str] = []

    def _record_error(stage: str, entity_id: str, exc: BaseException) -> None:
        errors.append(PipelineError(stage=stage, entity_id=entity_id, error=str(exc)))
        logger.error("%s failed for %s: %s", stage, entity_id, exc)
        if progress_cb:
            progress_cb(f"{stage}_error", entity_id)

    async def _bounded(scene_id: str, coro_factory: Callable[[], Awaitable[_T]]) -> None:
        async with semaphore:
            try:
                await run_with_retries(
                    coro_factory,
                    on_retry=lambda attempt, exc: logger.warning(
                        "Retrying translate for %s (attempt %d): %s", scene_id, attempt + 1, exc
                    ),
                )
                completed_scene_ids.append(scene_id)
                if progress_cb:
                    progress_cb("translate_done", scene_id)
            except PIPELINE_FAILURE_EXCEPTIONS as exc:
                _record_error("translate_scene", scene_id, exc)

    async with anyio.create_task_group() as tg:
        for sid in remaining_scene_ids:
            if progress_cb:
                progress_cb("translate_start", sid)
            tg.start_soon(
                _bounded,
                sid,
                lambda sid=sid: translate_scene(
                    context,
                    sid,
                    allow_overwrite=allow_overwrite,
                    checkpointer=effective_checkpointer,
                    decision_handler=decision_handler,
                    thread_id=f"{base_thread}:{sid}",
                ),
            )

    total_lines = 0
    for sid in completed_scene_ids:
        total_lines += len(await context.load_scene_lines(sid))

    result = TranslatorResult(
        scenes_translated=len(completed_scene_ids),
        lines_translated=total_lines,
        scenes_skipped=scenes_skipped,
        errors=errors,
    )

    logger.info("Translator pipeline complete: %s", result)
    if created_checkpointer and effective_checkpointer is not None:
        await maybe_close_checkpointer(effective_checkpointer)
    return result


def run_translator(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    allow_overwrite: bool = False,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
    progress_cb: Callable[[str, str], None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    checkpoint_enabled: bool = True,
) -> TranslatorResult:
    """Run the Translator pipeline to translate scenes.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to translate (default: all scenes).
        allow_overwrite: Allow overwriting existing translations.
        mode: Overwrite, gap-fill (default), or new-only behavior.
        concurrency: Maximum concurrent scene translations.
        decision_handler: Callback to collect HITL decisions when interrupts fire.
        thread_id: Optional thread id for checkpointer continuity.
        progress_cb: Optional callback invoked as (event, scene_id) per scene start.
        checkpointer: Optional LangGraph checkpoint saver to reuse (defaults to SQLite).
        checkpoint_enabled: Disable checkpoint persistence when False (uses in-memory).

    Returns:
        TranslatorResult: Statistics about what was translated.
    """
    return anyio.run(
        partial(
            _run_translator_async,
            project_path,
            scene_ids=scene_ids,
            allow_overwrite=allow_overwrite,
            mode=mode,
            concurrency=concurrency,
            decision_handler=decision_handler,
            thread_id=thread_id,
            progress_cb=progress_cb,
            checkpointer=checkpointer,
            checkpoint_enabled=checkpoint_enabled,
        )
    )


async def _filter_scenes_to_translate(
    context: TranslationContext,
    scene_ids: list[str],
    mode: Literal["overwrite", "gap-fill", "new-only"],
    allow_overwrite: bool,
) -> tuple[list[str], int]:
    """Return (scenes_to_run, scenes_skipped) based on mode and existing translations."""
    output_dir = context.project_path / "output" / "translations"
    remaining: list[str] = []
    skipped = 0

    for sid in scene_ids:
        output_file = output_dir / f"{sid}.jsonl"
        if allow_overwrite:
            remaining.append(sid)
            continue

        if not output_file.exists():
            remaining.append(sid)
            continue

        await context._load_translations(sid)
        total_lines = len(await context.load_scene_lines(sid))
        translated = context.get_translated_line_count(sid)

        if mode == "new-only":
            if translated == 0:
                remaining.append(sid)
            else:
                skipped += 1
            continue

        if mode == "gap-fill":
            if translated < total_lines:
                remaining.append(sid)
            else:
                skipped += 1
            continue

        # overwrite handled above
        remaining.append(sid)

    return remaining, skipped


class TranslationContext(Protocol):
    """Protocol for translation filtering to avoid tight coupling in tests."""

    project_path: Path

    async def _load_translations(self, scene_id: str) -> None: ...

    async def load_scene_lines(self, scene_id: str) -> list[SourceLine]:
        """Return source lines for the scene."""

    def get_translated_line_count(self, scene_id: str) -> int:
        """Return the number of translated lines for the scene."""
