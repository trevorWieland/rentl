"""Editor pipeline orchestrating QA subagents."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import partial
from pathlib import Path
from typing import Literal, Protocol, TypeVar

import anyio
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import BaseModel, Field
from rentl_agents.hitl.checkpoints import get_default_checkpointer, maybe_close_checkpointer
from rentl_agents.subagents.route_consistency_checker import (
    RouteConsistencyCheckResult,
    run_route_consistency_checks,
)
from rentl_agents.subagents.scene_style_checker import StyleCheckResult, run_style_checks
from rentl_agents.subagents.scene_translation_reviewer import (
    TranslationReviewResult,
    run_translation_review,
)
from rentl_core.context.project import ProjectContext, load_project_context
from rentl_core.model.line import TranslatedLine
from rentl_core.util.logging import get_logger

from rentl_pipelines.flows.utils import PIPELINE_FAILURE_EXCEPTIONS, PipelineError, SkippedItem, run_with_retries

logger = get_logger(__name__)
REPORT_FILENAME = "editor_report.json"


class EditorResult(BaseModel):
    """Results from the Editor pipeline."""

    scenes_checked: int = Field(description="Number of scenes QA'd.")
    scenes_skipped: int = Field(description="Number of scenes skipped based on mode or missing translations.")
    skipped: list[SkippedItem] = Field(default_factory=list, description="Skipped scenes with reasons.")
    translation_progress: float = Field(description="Percent of lines translated across all processed scenes.")
    editing_progress: float = Field(description="Percent of translated lines with at least one recorded check.")
    report_path: str | None = Field(default=None, description="Path to the written report, if any.")
    route_issue_counts: dict[str, int] = Field(
        default_factory=dict, description="Map of route_id to count of failing checks."
    )
    errors: list[PipelineError] = Field(default_factory=list, description="Errors encountered during QA.")


_T = TypeVar("_T")


class EditingContext(Protocol):
    """Protocol for editing context used in filtering utilities."""

    async def _load_translations(self, scene_id: str) -> None:
        """Load translations for a scene if they are not already cached."""

    async def get_translations(self, scene_id: str) -> list[TranslatedLine]:
        """Return translated lines for a scene."""


async def _run_editor_async(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    route_ids: list[str] | None = None,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
    progress_cb: Callable[[str, str], None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    report_path: Path | None = None,
    style_runner: Callable[..., Awaitable[StyleCheckResult]] | None = None,
    consistency_runner: Callable[..., Awaitable[RouteConsistencyCheckResult]] | None = None,
    review_runner: Callable[..., Awaitable[TranslationReviewResult]] | None = None,
    checkpoint_enabled: bool = True,
) -> EditorResult:
    """Run the Editor pipeline asynchronously.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to QA.
        route_ids: Optional list of route IDs whose scenes should be QA'd.
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
        checkpoint_enabled: Disable checkpoint persistence when False (uses in-memory).

    Returns:
        EditorResult: QA summary for the run.
    """
    logger.info("Starting Editor pipeline for %s", project_path)
    context = await load_project_context(project_path)
    created_checkpointer = checkpointer is None
    effective_checkpointer = (
        checkpointer
        if checkpointer is not None
        else await get_default_checkpointer(project_path / ".rentl" / "checkpoints.db")
        if checkpoint_enabled
        else None
    )
    output_reports_dir = project_path / "output" / "reports"
    if report_path is None:
        report_path = output_reports_dir / REPORT_FILENAME

    if route_ids:
        route_set = set(route_ids)
        target_scene_ids = sorted(
            {sid for sid, scene in context.scenes.items() if any(rid in route_set for rid in scene.route_ids)}
        )
    else:
        target_scene_ids = scene_ids if scene_ids else sorted(context.scenes.keys())
    if not target_scene_ids:
        return EditorResult(
            scenes_checked=0,
            scenes_skipped=0,
            skipped=[],
            translation_progress=0.0,
            editing_progress=0.0,
            report_path=None,
        )

    scenes_to_run, skipped_scenes = await _filter_scenes_to_edit(context, target_scene_ids, mode)
    if not scenes_to_run:
        report_payload, translation_progress, editing_progress, route_issue_counts = await _build_editor_report(
            context, target_scene_ids, report_path
        )
        await _write_editor_report(report_path, report_payload)
        result = EditorResult(
            scenes_checked=0,
            scenes_skipped=len(skipped_scenes),
            skipped=skipped_scenes,
            translation_progress=translation_progress,
            editing_progress=editing_progress,
            report_path=str(report_path),
            route_issue_counts=route_issue_counts,
            errors=[],
        )
        if created_checkpointer and effective_checkpointer is not None:
            await maybe_close_checkpointer(effective_checkpointer)
        return result

    _ = (decision_handler, thread_id)
    semaphore = anyio.Semaphore(max(1, concurrency))
    errors: list[PipelineError] = []
    completed_scene_ids: list[str] = []
    base_thread = thread_id or ("edit:routes:" + ",".join(sorted(route_ids)) if route_ids else "edit")
    style_runner = style_runner or run_style_checks
    consistency_runner = consistency_runner or run_route_consistency_checks
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
        for sid in scenes_to_run:
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
        for sid in scenes_to_run:
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
        for sid in scenes_to_run:
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

    report_payload, translation_progress, editing_progress, route_issue_counts = await _build_editor_report(
        context, target_scene_ids, report_path
    )
    result = EditorResult(
        scenes_checked=len(set(completed_scene_ids)),
        scenes_skipped=len(skipped_scenes),
        skipped=skipped_scenes,
        translation_progress=translation_progress,
        editing_progress=editing_progress,
        report_path=str(report_path),
        route_issue_counts=route_issue_counts,
        errors=errors,
    )
    await _write_editor_report(report_path, report_payload)
    logger.info("Editor pipeline complete: %s", result)
    if created_checkpointer and effective_checkpointer is not None:
        await maybe_close_checkpointer(effective_checkpointer)
    return result


def run_editor(
    project_path: Path,
    *,
    scene_ids: list[str] | None = None,
    route_ids: list[str] | None = None,
    mode: Literal["overwrite", "gap-fill", "new-only"] = "gap-fill",
    concurrency: int = 4,
    decision_handler: Callable[[list[str]], list[str | dict[str, str]]] | None = None,
    thread_id: str | None = None,
    progress_cb: Callable[[str, str], None] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    report_path: Path | None = None,
    style_runner: Callable[..., Awaitable[StyleCheckResult]] | None = None,
    consistency_runner: Callable[..., Awaitable[RouteConsistencyCheckResult]] | None = None,
    review_runner: Callable[..., Awaitable[TranslationReviewResult]] | None = None,
    checkpoint_enabled: bool = True,
) -> EditorResult:
    """Run the Editor pipeline.

    Args:
        project_path: Path to the game project.
        scene_ids: Optional list of specific scene IDs to QA.
        route_ids: Optional list of route IDs whose scenes should be QA'd.
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
        checkpoint_enabled: Disable checkpoint persistence when False (uses in-memory).

    Returns:
        EditorResult: QA summary for the run.
    """
    return anyio.run(
        partial(
            _run_editor_async,
            project_path,
            scene_ids=scene_ids,
            route_ids=route_ids,
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
            checkpoint_enabled=checkpoint_enabled,
        )
    )


async def _build_editor_report(
    context: ProjectContext, scene_ids: list[str], report_path: Path
) -> tuple[dict[str, object], float, float, dict[str, int]]:
    """Aggregate translation/editing progress and findings for a report.

    Returns:
        tuple[dict[str, object], float, float, dict[str, int]]:
        (payload, translation_progress_pct, editing_progress_pct, route_issue_counts)
    """
    total_lines = 0
    translated_lines = 0
    checked_lines = 0
    scenes_payload: list[dict[str, object]] = []
    top_issues: list[dict[str, object]] = []

    translations_by_scene: dict[str, list[TranslatedLine]] = {}
    for sid in scene_ids:
        lines = await context.load_scene_lines(sid)
        total_lines += len(lines)
        await context._load_translations(sid)
        translations = await context.get_translations(sid)
        translations_by_scene[sid] = translations
        translated_lines += len(translations)
        line_findings: list[dict[str, object]] = []
        scene_checked_lines = 0
        for t in translations:
            if t.meta.checks:
                scene_checked_lines += 1
                check_payload = {
                    name: {"passed": bool(passed), "note": note} for name, (passed, note) in t.meta.checks.items()
                }
                line_findings.append(
                    {
                        "line_id": t.id,
                        "checks": check_payload,
                    }
                )
                failing = {name: meta for name, meta in check_payload.items() if not meta["passed"]}
                if failing:
                    top_issues.append(
                        {
                            "scene_id": sid,
                            "line_id": t.id,
                            "checks": failing,
                        }
                    )
        checked_lines += scene_checked_lines
        scene_translation_progress = (len(translations) / len(lines) * 100) if lines else 0.0
        scene_editing_progress = (scene_checked_lines / len(translations) * 100) if translations else 0.0
        scenes_payload.append(
            {
                "scene_id": sid,
                "translation_progress_pct": round(scene_translation_progress, 1),
                "editing_progress_pct": round(scene_editing_progress, 1),
                "findings": line_findings,
            }
        )

    routes_payload: list[dict[str, object]] = []
    route_issue_map: dict[str, list[dict[str, object]]] = {}
    for route in context.routes.values():
        relevant_scene_ids = [sid for sid in route.scene_ids if sid in scene_ids]
        if not relevant_scene_ids:
            continue
        route_lines = 0
        route_translated = 0
        route_checked = 0
        route_issues: list[dict[str, object]] = []
        for sid in relevant_scene_ids:
            lines = await context.load_scene_lines(sid)
            route_lines += len(lines)
            await context._load_translations(sid)
            translations = await context.get_translations(sid)
            route_translated += len(translations)
            for t in translations:
                if t.meta.checks:
                    route_checked += 1
                    failing = {name: meta for name, meta in t.meta.checks.items() if not meta[0]}
                    if failing:
                        route_issues.append(
                            {
                                "scene_id": sid,
                                "line_id": t.id,
                                "checks": {k: {"passed": v[0], "note": v[1]} for k, v in failing.items()},
                            }
                        )
        route_issue_map[route.id] = route_issues
        routes_payload.append(
            {
                "route_id": route.id,
                "translation_progress_pct": round((route_translated / route_lines * 100) if route_lines else 0.0, 1),
                "editing_progress_pct": round((route_checked / route_translated * 100) if route_translated else 0.0, 1),
                "issues": route_issues[:5],
            }
        )

    translation_progress = (translated_lines / total_lines * 100) if total_lines else 0.0
    editing_progress = (checked_lines / translated_lines * 100) if translated_lines else 0.0

    payload = {
        "summary": {
            "scenes": len(scene_ids),
            "translation_progress_pct": round(translation_progress, 1),
            "editing_progress_pct": round(editing_progress, 1),
        },
        "routes": routes_payload,
        "scenes": scenes_payload,
        "top_issues": top_issues[:10],
        "route_top_issues": {rid: issues[:5] for rid, issues in route_issue_map.items()},
        "report_path": str(report_path),
        "skipped_scenes": [
            {
                "scene_id": sid,
                "reason": "No translations found; run translate first."
                if not translations_by_scene.get(sid)
                else "Already fully QA'd",
            }
            for sid in scene_ids
            if not translations_by_scene.get(sid)
            or all(line.meta.checks for line in translations_by_scene.get(sid, []))
        ],
    }
    route_issue_counts = {rid: len(issues) for rid, issues in route_issue_map.items()}
    return payload, translation_progress, editing_progress, route_issue_counts


async def _write_editor_report(path: Path, payload: dict[str, object]) -> None:
    """Persist a JSON report summarizing editor results."""
    import orjson

    await anyio.Path(path.parent).mkdir(parents=True, exist_ok=True)
    async with await anyio.open_file(path, "wb") as stream:
        await stream.write(orjson.dumps(payload, option=orjson.OPT_INDENT_2))


async def _filter_scenes_to_edit(
    context: EditingContext, scene_ids: list[str], mode: Literal["overwrite", "gap-fill", "new-only"]
) -> tuple[list[str], list[SkippedItem]]:
    """Return scenes that still need editing based on mode and QA coverage.

    Returns:
        tuple[list[str], list[SkippedItem]]: (scenes_to_run, skipped_scenes_with_reasons)
    """
    remaining: list[str] = []
    skipped: list[SkippedItem] = []
    for sid in scene_ids:
        await context._load_translations(sid)
        translations = await context.get_translations(sid)
        if not translations:
            skipped.append(SkippedItem(entity_id=sid, reason="No translations found; run translate first."))
            continue

        translated = len(translations)
        checked = sum(1 for line in translations if line.meta.checks)

        if mode == "overwrite":
            remaining.append(sid)
            continue

        if mode == "new-only":
            if checked == 0:
                remaining.append(sid)
            else:
                skipped.append(
                    SkippedItem(entity_id=sid, reason="Already has QA checks; use gap-fill or overwrite to re-run.")
                )
            continue

        if mode == "gap-fill" and checked < translated:
            remaining.append(sid)
            continue

        if mode in {"gap-fill", "new-only"} and checked >= translated:
            skipped.append(SkippedItem(entity_id=sid, reason="Already fully QA'd for this mode."))

    return remaining, skipped
