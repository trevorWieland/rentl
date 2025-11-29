"""CLI commands for running pipelines."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree
from typing import Annotated, Literal

import orjson
import typer
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext, load_project_context
from rentl_core.util.logging import configure_logging
from rentl_pipelines.flows.context_builder import (
    _filter_characters,
    _filter_locations,
    _filter_routes,
    _filter_scenes,
    run_context_builder,
)
from rentl_pipelines.flows.editor import run_editor
from rentl_pipelines.flows.translator import run_translator
from rentl_pipelines.flows.utils import PipelineError, SkippedItem

from rentl_cli.cli_types import ProjectPathOption
from rentl_cli.utils.baseline import write_baseline
from rentl_cli.utils.resume import choose_thread_id
from rentl_cli.utils.status_snapshot import (
    PhaseFailure,
    PhaseProgress,
    load_phase_status,
    record_phase_snapshot,
    record_phase_start,
)


def _prompt_decisions(requests: list[str]) -> list[str | dict[str, str]]:
    """Prompt the user for HITL decisions in the CLI.

    Args:
        requests: Approval request messages from the agent.

    Returns:
        list[str | dict[str, str]]: Decisions corresponding to each request.
    """
    decisions: list[str | dict[str, str]] = []
    for request in requests:
        typer.secho("\nHITL approval requested:", fg=typer.colors.YELLOW, bold=True)
        typer.echo(request)
        decision = typer.prompt("Decision [approve/reject]", default="approve")
        if decision.lower() not in {"approve", "reject"}:
            typer.secho("Invalid choice, defaulting to 'reject'.", fg=typer.colors.RED)
            decision = "reject"
        decisions.append(decision.lower())
    return decisions


class SnapshotSkippedScene(BaseModel):
    """Skipped scene entry for status snapshots."""

    scene_id: str = Field(description="Identifier of the skipped scene.")
    reason: str = Field(description="Reason the scene was skipped.")


class SnapshotRouteProgress(BaseModel):
    """Route-level progress for status snapshots."""

    route_id: str = Field(description="Route identifier.")
    total_lines: int = Field(description="Total source lines in the route.")
    translated_lines: int = Field(description="Translated lines in the route.")
    checked_lines: int = Field(description="Lines with QA checks in the route.")
    failing_checks: int = Field(description="Number of failing QA checks in the route.")
    translation_progress_pct: float = Field(description="Percent of lines translated in the route.")
    editing_progress_pct: float = Field(description="Percent of translated lines QA'd in the route.")


class SnapshotCheckpoint(BaseModel):
    """Checkpoint metadata for resume hints."""

    path: str = Field(description="Path to the checkpoint database.")
    modified: datetime = Field(description="Last modified timestamp.")


class SnapshotProgress(BaseModel):
    """Status snapshot payload for CLI/TUI consumption."""

    translation_progress_pct: float = Field(description="Overall translation progress percent.")
    editing_progress_pct: float = Field(description="Overall editing progress percent.")
    total_lines: int = Field(description="Total source lines across all scenes.")
    translated_lines: int = Field(description="Translated lines across all scenes.")
    checked_lines: int = Field(description="Lines with QA checks across all scenes.")
    failing_checks: int = Field(description="Total failing QA checks.")
    routes: list[SnapshotRouteProgress] = Field(description="Per-route progress.")
    checkpoint: SnapshotCheckpoint | None = Field(description="Latest checkpoint metadata, if present.")
    thread_id_hints: list[str] = Field(description="Suggested thread id formats for resumable runs.")
    skipped_context_scenes: list[SnapshotSkippedScene] = Field(
        description="Scenes skipped for context due to completeness."
    )
    skipped_translation_scenes: list[SnapshotSkippedScene] = Field(
        description="Scenes skipped for translation due to completeness."
    )
    generated_at: datetime = Field(description="Snapshot generation timestamp.")


def _progress_printer(verbose: bool) -> Callable[[str, str], None] | None:
    """Return a progress callback that logs events when verbose is enabled."""
    if not verbose:
        return None

    def _cb(event: str, entity: str) -> None:
        typer.echo(f"[progress] {event} :: {entity}")

    return _cb


def _format_errors(errors: list[PipelineError]) -> list[str]:
    """Render pipeline errors for snapshot persistence.

    Returns:
        list[str]: Flattened error strings for status snapshots.
    """
    return [f"{err.stage}:{err.entity_id}:{err.error}" for err in errors]


def _resolve_log_file(project_path: Path, log_file: Path | None) -> Path:
    """Return the log file path, defaulting under .rentl/logs."""
    if log_file:
        return log_file
    return project_path / ".rentl" / "logs" / "rentl.log"


async def _collect_progress_snapshot(context: ProjectContext) -> SnapshotProgress:
    """Compute translation/editing progress for public-facing sharing.

    Returns:
        SnapshotProgress: Structured snapshot with progress percentages, skips, and checkpoint hints.
    """
    total_lines = 0
    translated_lines = 0
    checked_lines = 0
    total_issues = 0
    routes_payload: list[SnapshotRouteProgress] = []

    skipped_translation: list[dict[str, str]] = []
    skipped_context: list[dict[str, str]] = []
    for sid in context.scenes:
        lines = await context.load_scene_lines(sid)
        total_lines += len(lines)
        await context._load_translations(sid)
        translations = await context.get_translations(sid)
        translated_lines += len(translations)
        if translations and len(translations) == len(lines):
            skipped_translation.append({"scene_id": sid, "reason": "Fully translated"})
        ann = context.get_scene(sid).annotations
        if all([ann.summary, ann.tags, ann.primary_characters, ann.locations]):
            skipped_context.append({"scene_id": sid, "reason": "Context complete"})
        for t in translations:
            if t.meta.checks:
                checked_lines += 1
                total_issues += sum(1 for passed, _ in t.meta.checks.values() if not passed)

    for route in sorted(context.routes.values(), key=lambda r: r.id):
        route_lines = 0
        route_translated = 0
        route_checked = 0
        route_issues = 0
        for sid in route.scene_ids:
            lines = await context.load_scene_lines(sid)
            route_lines += len(lines)
            await context._load_translations(sid)
            translations = await context.get_translations(sid)
            route_translated += len(translations)
            for t in translations:
                if t.meta.checks:
                    route_checked += 1
                    route_issues += sum(1 for passed, _ in t.meta.checks.values() if not passed)
        routes_payload.append(
            SnapshotRouteProgress(
                route_id=route.id,
                total_lines=route_lines,
                translated_lines=route_translated,
                checked_lines=route_checked,
                failing_checks=route_issues,
                translation_progress_pct=round((route_translated / route_lines * 100) if route_lines else 0.0, 1),
                editing_progress_pct=round((route_checked / route_translated * 100) if route_translated else 0.0, 1),
            )
        )

    translation_progress = (translated_lines / total_lines * 100) if total_lines else 0.0
    editing_progress = (checked_lines / translated_lines * 100) if translated_lines else 0.0

    checkpoint_path = context.project_path / ".rentl" / "checkpoints.db"
    checkpoint_info: SnapshotCheckpoint | None = None
    if checkpoint_path.exists():
        mtime = checkpoint_path.stat().st_mtime
        checkpoint_info = SnapshotCheckpoint(path=str(checkpoint_path), modified=datetime.fromtimestamp(mtime, UTC))

    return SnapshotProgress(
        translation_progress_pct=round(translation_progress, 1),
        editing_progress_pct=round(editing_progress, 1),
        total_lines=total_lines,
        translated_lines=translated_lines,
        checked_lines=checked_lines,
        failing_checks=total_issues,
        routes=routes_payload,
        checkpoint=checkpoint_info,
        thread_id_hints=["context-<uuid>", "translate-<uuid>", "edit-<uuid>"],
        skipped_context_scenes=[
            SnapshotSkippedScene(scene_id=item["scene_id"], reason=item["reason"]) for item in skipped_context
        ],
        skipped_translation_scenes=[
            SnapshotSkippedScene(scene_id=item["scene_id"], reason=item["reason"]) for item in skipped_translation
        ],
        generated_at=datetime.now(UTC),
    )


def _print_top_issues(report_path: str) -> None:
    """Pretty-print top issues from the editor report if present."""
    data = orjson.loads(Path(report_path).read_bytes())

    top_issues = data.get("top_issues") or []
    if not top_issues:
        return
    typer.secho("  Top issues:", fg=typer.colors.YELLOW)
    for issue in top_issues[:3]:
        scene_id = issue.get("scene_id", "<unknown>")
        line_id = issue.get("line_id", "<unknown>")
        checks = issue.get("checks", {})
        failing = ", ".join(checks.keys()) if isinstance(checks, dict) else ""
        typer.echo(f"    {scene_id} {line_id}: {failing}")


def status(
    project_path: ProjectPathOption = Path("."),
    by_route: Annotated[bool, typer.Option("--by-route", help="Include per-route progress.")] = False,
    snapshot_json: Annotated[
        bool, typer.Option("--snapshot-json", help="Emit public-facing translation/editing progress as JSON.")
    ] = False,
    public_only: Annotated[
        bool, typer.Option("--public", help="Output only the public JSON snapshot (no extra text).")
    ] = False,
) -> None:
    """Show quick pipeline status for a project (scenes, characters, translations)."""

    async def _status_async(path: Path) -> None:
        context = await load_project_context(path)
        progress = await _collect_progress_snapshot(context)
        phase_status = load_phase_status(path)
        scenes = context.scenes.values()
        characters = context.characters.values()
        locations = context.locations.values()
        routes = context.routes.values()

        scenes_incomplete, _ = _filter_scenes(scenes, "gap-fill")
        characters_incomplete = _filter_characters(characters, "gap-fill")
        locations_incomplete = _filter_locations(locations, "gap-fill")
        routes_incomplete = _filter_routes(routes, "gap-fill")
        hints: list[str] = []
        if phase_status:
            hints = [
                snap.thread_id
                for snap in (phase_status.context, phase_status.translate, phase_status.edit)
                if snap is not None
            ]

        if not public_only:
            typer.secho("Status", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"  Scenes: {len(scenes)} total / {len(scenes_incomplete)} incomplete")
            typer.echo(f"  Characters: {len(characters)} total / {len(characters_incomplete)} incomplete")
            typer.echo(f"  Locations: {len(locations)} total / {len(locations_incomplete)} incomplete")
            typer.echo(f"  Routes: {len(routes)} total / {len(routes_incomplete)} incomplete")
            typer.echo(
                f"  Translation Progress: {progress.translation_progress_pct:.1f}% "
                f"({progress.translated_lines}/{progress.total_lines} lines)"
            )
            typer.echo(
                f"  Editing Progress: {progress.editing_progress_pct:.1f}% "
                f"({progress.checked_lines}/{progress.translated_lines} translated lines)"
            )
            typer.echo(f"  Failing Checks: {progress.failing_checks}")

        if phase_status and not public_only:
            typer.secho("\n  Last runs:", fg=typer.colors.CYAN, bold=True)
            for key, label in (("context", "Context"), ("translate", "Translate"), ("edit", "Edit")):
                snap = (
                    phase_status.context
                    if key == "context"
                    else phase_status.translate
                    if key == "translate"
                    else phase_status.edit
                )
                if not snap:
                    continue
                ts = snap.updated_at.isoformat(timespec="seconds")
                err_count = len(snap.errors)
                detail_str = ""
                if snap.details:
                    detail_str = "; ".join(f"{k}={v}" for k, v in snap.details.items())
                    if detail_str:
                        detail_str = f" [{detail_str}]"
                progress_str = ""
                if snap.progress and snap.progress.progress_pct is not None:
                    progress_str = f" progress={snap.progress.progress_pct:.1f}%"
                if snap.progress and snap.progress.elapsed_seconds is not None:
                    progress_str += f" elapsed={snap.progress.elapsed_seconds:.1f}s"
                if snap.route_scope:
                    progress_str += f" routes={','.join(snap.route_scope)}"
                typer.echo(
                    f"    {label}: thread {snap.thread_id} mode={snap.mode or 'n/a'} "
                    f"status={snap.status} errors={err_count} at {ts}{detail_str}{progress_str}"
                )
                if snap.errors:
                    for err in snap.errors[:5]:
                        typer.echo(f"      - {err}")
                    if err_count > 5:
                        typer.echo(f"      ... ({err_count - 5} more)")
        if hints:
            progress.thread_id_hints = hints

        if by_route and not public_only:
            typer.secho("\n  By Route:", fg=typer.colors.CYAN, bold=True)
            for route in progress.routes:
                t_pct = route.translation_progress_pct
                e_pct = route.editing_progress_pct
                route_lines = route.total_lines
                route_translated = route.translated_lines
                route_checked = route.checked_lines
                failing = route.failing_checks
                typer.echo(
                    f"    {route.route_id}: translate {t_pct:.1f}% ({route_translated}/{route_lines}), "
                    f"edit {e_pct:.1f}% ({route_checked}/{route_translated or 1}), "
                    f"failing checks {failing}"
                )

        if not public_only:
            checkpoint_path = path / ".rentl" / "checkpoints.db"
            if checkpoint_path.exists():
                mtime = checkpoint_path.stat().st_mtime
                from datetime import datetime

                ts = datetime.fromtimestamp(mtime).isoformat(timespec="seconds")
                typer.echo(f"  Checkpoints: found at {checkpoint_path} (updated {ts}); reuse with --thread-id")
            else:
                typer.echo("  Checkpoints: none (using in-memory)")

        skipped_ctx = progress.skipped_context_scenes
        skipped_tx = progress.skipped_translation_scenes
        if skipped_ctx and not public_only:
            typer.secho("  Skipped context scenes:", fg=typer.colors.YELLOW)
            for entry in skipped_ctx:
                typer.echo(f"    {entry.scene_id}: {entry.reason}")
        if skipped_tx and not public_only:
            typer.secho("  Skipped translation scenes:", fg=typer.colors.YELLOW)
            for entry in skipped_tx:
                typer.echo(f"    {entry.scene_id}: {entry.reason}")

        if snapshot_json or public_only:
            if not public_only:
                typer.echo("\nPublic progress snapshot (JSON):")
            typer.echo(progress.model_dump_json(indent=2))

    typer.echo("Collecting project status...")
    import anyio

    anyio.run(_status_async, project_path)


def _print_skipped(scenes: list[SkippedItem], label: str) -> None:
    """Print skipped scene details."""
    if not scenes:
        return
    typer.secho(f"  {label}:", fg=typer.colors.YELLOW)
    for entry in scenes:
        typer.echo(f"    {entry.entity_id}: {entry.reason}")


def context(
    project_path: ProjectPathOption = Path("."),
    route_ids: Annotated[
        list[str] | None, typer.Option("--route", "-r", help="Route IDs to process (default: all).")
    ] = None,
    scene_ids: Annotated[
        list[str] | None, typer.Option("--scene", "-s", help="Specific scene IDs to process (default: all).")
    ] = None,
    overwrite: Annotated[bool, typer.Option(help="Allow overwriting existing metadata.")] = False,
    mode: Annotated[
        Literal["overwrite", "gap-fill", "new-only"],
        typer.Option(help="Processing mode: overwrite, gap-fill (default), or new-only"),
    ] = "gap-fill",
    concurrency: Annotated[int, typer.Option(help="Maximum concurrent detailer runs.")] = 4,
    thread_id: Annotated[str | None, typer.Option(help="Resume/identify a HITL run by thread id.")] = None,
    resume: Annotated[bool, typer.Option(help="Resume a previous run; requires --thread-id.")] = False,
    resume_latest: Annotated[
        bool, typer.Option(help="Resume the most recent checkpoint thread id (ignores --thread-id).")
    ] = False,
    no_checkpoint: Annotated[bool, typer.Option("--no-checkpoint", help="Disable checkpoint persistence.")] = False,
    verbosity: Annotated[
        Literal["info", "verbose", "debug"], typer.Option("--verbosity", "-v", help="Console verbosity level.")
    ] = "info",
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", help="Write detailed logs to this file (default: .rentl/logs/rentl.log)."),
    ] = None,
) -> None:
    """Run the Context Builder pipeline to enrich all game metadata."""
    configure_logging(verbosity, _resolve_log_file(project_path, log_file))
    typer.secho("Starting Context Builder pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = choose_thread_id(
        prefix="context",
        resume=resume,
        resume_latest=resume_latest,
        thread_id=thread_id,
        no_checkpoint=no_checkpoint,
        checkpoint_path=project_path / ".rentl" / "checkpoints.db",
        project_path=project_path,
        route_ids=route_ids,
    )
    record_phase_start(project_path, "context", thread_id=thread_id, mode=mode, route_ids=route_ids)
    result = run_context_builder(
        project_path,
        allow_overwrite=overwrite,
        mode=mode,
        scene_ids=scene_ids or None,
        route_ids=route_ids or None,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
        progress_cb=_progress_printer(verbosity != "info"),
        checkpoint_enabled=not no_checkpoint,
    )

    start_snapshot = load_phase_status(project_path)
    started_at = start_snapshot.context.started_at if start_snapshot and start_snapshot.context else None
    elapsed_seconds = (datetime.now(UTC) - started_at).total_seconds() if started_at else None
    completed_items = (
        result.scenes_detailed
        + result.characters_detailed
        + result.locations_detailed
        + result.routes_detailed
        + result.glossary_entries_added
        + result.glossary_entries_updated
    )
    total_items = completed_items + result.scenes_skipped
    progress_pct = (completed_items / total_items * 100) if total_items else None
    estimated_total_seconds = (
        (elapsed_seconds / completed_items * total_items) if elapsed_seconds and completed_items else elapsed_seconds
    )
    estimated_remaining_seconds = (
        max(estimated_total_seconds - elapsed_seconds, 0) if estimated_total_seconds and elapsed_seconds else None
    )
    progress = PhaseProgress(
        total_items=total_items,
        completed_items=completed_items,
        skipped_items=result.scenes_skipped,
        progress_pct=progress_pct,
        elapsed_seconds=elapsed_seconds,
        estimated_total_seconds=estimated_total_seconds,
        estimated_remaining_seconds=estimated_remaining_seconds,
    )
    failures = [PhaseFailure(stage=err.stage, entity_id=err.entity_id, error=err.error) for err in result.errors]
    record_phase_snapshot(
        project_path,
        "context",
        thread_id=thread_id,
        mode=mode,
        details={
            "scenes_detailed": result.scenes_detailed,
            "characters_detailed": result.characters_detailed,
            "locations_detailed": result.locations_detailed,
            "routes_detailed": result.routes_detailed,
            "skipped_scenes": result.scenes_skipped,
            "glossary_entries_added": result.glossary_entries_added,
            "glossary_entries_updated": result.glossary_entries_updated,
        },
        errors=_format_errors(result.errors),
        failures=failures,
        started_at=started_at,
        progress=progress,
        route_ids=route_ids,
    )

    # Display results
    typer.secho("\nContext Builder Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes detailed: {result.scenes_detailed}")
    typer.echo(f"  Scenes skipped: {result.scenes_skipped}")
    typer.echo(f"  Characters detailed: {result.characters_detailed}")
    typer.echo(f"  Locations detailed: {result.locations_detailed}")
    typer.echo(f"  Glossary entries added: {result.glossary_entries_added}")
    typer.echo(f"  Glossary entries updated: {result.glossary_entries_updated}")
    typer.echo(f"  Routes detailed: {result.routes_detailed}")
    typer.echo(f"  Resume thread id: {thread_id}")
    _print_skipped(result.skipped_scenes, "Skipped scenes")
    if result.errors:
        typer.secho(f"  Errors: {len(result.errors)} (see logs for details)", fg=typer.colors.RED)


def translate(
    project_path: ProjectPathOption = Path("."),
    scene_ids: Annotated[
        list[str] | None, typer.Option("--scene", "-s", help="Specific scene IDs to translate (default: all).")
    ] = None,
    route_ids: Annotated[
        list[str] | None, typer.Option("--route", "-r", help="Route IDs to translate (default: all).")
    ] = None,
    overwrite: Annotated[bool, typer.Option(help="Allow overwriting existing translations.")] = False,
    mode: Annotated[
        Literal["overwrite", "gap-fill", "new-only"],
        typer.Option(help="Processing mode: overwrite, gap-fill (default), or new-only"),
    ] = "gap-fill",
    concurrency: Annotated[int, typer.Option(help="Maximum concurrent scene translations.")] = 4,
    thread_id: Annotated[str | None, typer.Option(help="Resume/identify a HITL run by thread id.")] = None,
    resume: Annotated[bool, typer.Option(help="Resume a previous run; requires --thread-id.")] = False,
    resume_latest: Annotated[
        bool, typer.Option(help="Resume the most recent checkpoint thread id (ignores --thread-id).")
    ] = False,
    no_checkpoint: Annotated[bool, typer.Option("--no-checkpoint", help="Disable checkpoint persistence.")] = False,
    verbosity: Annotated[
        Literal["info", "verbose", "debug"], typer.Option("--verbosity", "-v", help="Console verbosity level.")
    ] = "info",
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", help="Write detailed logs to this file (default: .rentl/logs/rentl.log)."),
    ] = None,
) -> None:
    """Run the Translator pipeline to translate scenes."""
    configure_logging(verbosity, _resolve_log_file(project_path, log_file))
    typer.secho("Starting Translator pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = choose_thread_id(
        prefix="translate",
        resume=resume,
        resume_latest=resume_latest,
        thread_id=thread_id,
        no_checkpoint=no_checkpoint,
        checkpoint_path=project_path / ".rentl" / "checkpoints.db",
        project_path=project_path,
        route_ids=route_ids,
    )
    record_phase_start(project_path, "translate", thread_id=thread_id, mode=mode, route_ids=route_ids)
    result = run_translator(
        project_path,
        scene_ids=scene_ids or None,
        route_ids=route_ids or None,
        allow_overwrite=overwrite,
        mode=mode,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
        progress_cb=_progress_printer(verbosity != "info"),
        checkpoint_enabled=not no_checkpoint,
    )

    start_snapshot = load_phase_status(project_path)
    started_at = start_snapshot.translate.started_at if start_snapshot and start_snapshot.translate else None
    elapsed_seconds = (datetime.now(UTC) - started_at).total_seconds() if started_at else None
    completed_items = result.scenes_translated
    total_items = result.scenes_translated + result.scenes_skipped
    progress_pct = (completed_items / total_items * 100) if total_items else None
    estimated_total_seconds = (
        (elapsed_seconds / completed_items * total_items) if elapsed_seconds and completed_items else elapsed_seconds
    )
    estimated_remaining_seconds = (
        max(estimated_total_seconds - elapsed_seconds, 0) if estimated_total_seconds and elapsed_seconds else None
    )
    progress = PhaseProgress(
        total_items=total_items,
        completed_items=completed_items,
        skipped_items=result.scenes_skipped,
        progress_pct=progress_pct,
        elapsed_seconds=elapsed_seconds,
        estimated_total_seconds=estimated_total_seconds,
        estimated_remaining_seconds=estimated_remaining_seconds,
    )
    failures = [PhaseFailure(stage=err.stage, entity_id=err.entity_id, error=err.error) for err in result.errors]
    record_phase_snapshot(
        project_path,
        "translate",
        thread_id=thread_id,
        mode=mode,
        details={
            "scenes_translated": result.scenes_translated,
            "lines_translated": result.lines_translated,
            "scenes_skipped": result.scenes_skipped,
        },
        errors=_format_errors(result.errors),
        failures=failures,
        started_at=started_at,
        progress=progress,
        route_ids=route_ids,
    )

    # Display results
    typer.secho("\nTranslator Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes translated: {result.scenes_translated}")
    typer.echo(f"  Lines translated: {result.lines_translated}")
    typer.echo(f"  Scenes skipped: {result.scenes_skipped}")
    typer.echo(f"  Resume thread id: {thread_id}")
    _print_skipped(result.skipped, "Skipped scenes")
    if result.errors:
        typer.secho(f"  Errors: {len(result.errors)} (see logs for details)", fg=typer.colors.RED)


def edit(
    project_path: ProjectPathOption = Path("."),
    scene_ids: Annotated[
        list[str] | None, typer.Option("--scene", "-s", help="Specific scene IDs to QA (default: all).")
    ] = None,
    route_ids: Annotated[
        list[str] | None, typer.Option("--route", "-r", help="Route IDs to QA (default: all).")
    ] = None,
    mode: Annotated[
        Literal["overwrite", "gap-fill", "new-only"],
        typer.Option(help="Processing mode: overwrite, gap-fill (default), or new-only"),
    ] = "gap-fill",
    concurrency: Annotated[int, typer.Option(help="Maximum concurrent QA runs.")] = 4,
    thread_id: Annotated[str | None, typer.Option(help="Resume/identify a HITL run by thread id.")] = None,
    resume: Annotated[bool, typer.Option(help="Resume a previous run; requires --thread-id.")] = False,
    resume_latest: Annotated[
        bool, typer.Option(help="Resume the most recent checkpoint thread id (ignores --thread-id).")
    ] = False,
    no_checkpoint: Annotated[bool, typer.Option("--no-checkpoint", help="Disable checkpoint persistence.")] = False,
    verbosity: Annotated[
        Literal["info", "verbose", "debug"], typer.Option("--verbosity", "-v", help="Console verbosity level.")
    ] = "info",
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", help="Write detailed logs to this file (default: .rentl/logs/rentl.log)."),
    ] = None,
) -> None:
    """Run the Editor pipeline to perform QA on translations."""
    configure_logging(verbosity, _resolve_log_file(project_path, log_file))
    typer.secho("Starting Editor pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = choose_thread_id(
        prefix="edit",
        resume=resume,
        resume_latest=resume_latest,
        thread_id=thread_id,
        no_checkpoint=no_checkpoint,
        checkpoint_path=project_path / ".rentl" / "checkpoints.db",
        project_path=project_path,
        route_ids=route_ids,
    )
    record_phase_start(project_path, "edit", thread_id=thread_id, mode=mode, route_ids=route_ids)
    result = run_editor(
        project_path,
        scene_ids=scene_ids or None,
        route_ids=route_ids or None,
        mode=mode,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
        progress_cb=_progress_printer(verbosity != "info"),
        checkpoint_enabled=not no_checkpoint,
    )

    start_snapshot = load_phase_status(project_path)
    started_at = start_snapshot.edit.started_at if start_snapshot and start_snapshot.edit else None
    elapsed_seconds = (datetime.now(UTC) - started_at).total_seconds() if started_at else None
    completed_items = result.scenes_checked
    total_items = result.scenes_checked + result.scenes_skipped
    progress_pct = (completed_items / total_items * 100) if total_items else None
    estimated_total_seconds = (
        (elapsed_seconds / completed_items * total_items) if elapsed_seconds and completed_items else elapsed_seconds
    )
    estimated_remaining_seconds = (
        max(estimated_total_seconds - elapsed_seconds, 0) if estimated_total_seconds and elapsed_seconds else None
    )
    progress = PhaseProgress(
        total_items=total_items,
        completed_items=completed_items,
        skipped_items=result.scenes_skipped,
        progress_pct=progress_pct,
        elapsed_seconds=elapsed_seconds,
        estimated_total_seconds=estimated_total_seconds,
        estimated_remaining_seconds=estimated_remaining_seconds,
    )
    failures = [PhaseFailure(stage=err.stage, entity_id=err.entity_id, error=err.error) for err in result.errors]
    record_phase_snapshot(
        project_path,
        "edit",
        thread_id=thread_id,
        mode=mode,
        details={
            "scenes_checked": result.scenes_checked,
            "scenes_skipped": result.scenes_skipped,
            "translation_progress_pct": result.translation_progress,
            "editing_progress_pct": result.editing_progress,
        },
        errors=_format_errors(result.errors),
        failures=failures,
        started_at=started_at,
        progress=progress,
        route_ids=route_ids,
    )

    typer.secho("\nEditor Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes checked: {result.scenes_checked}")
    typer.echo(f"  Scenes skipped: {result.scenes_skipped}")
    typer.echo(f"  Translation Progress: {result.translation_progress:.1f}%")
    typer.echo(f"  Editing Progress: {result.editing_progress:.1f}%")
    if result.report_path:
        typer.echo(f"  Report: {result.report_path}")
        _print_top_issues(result.report_path)
    if result.route_issue_counts:
        typer.secho("  Route issue counts:", fg=typer.colors.YELLOW)
        for rid, count in sorted(result.route_issue_counts.items()):
            typer.echo(f"    {rid}: {count} failing checks")
    typer.echo(f"  Resume thread id: {thread_id}")
    _print_skipped(result.skipped, "Skipped scenes")
    if result.errors:
        typer.secho(f"  Errors: {len(result.errors)} (see logs for details)", fg=typer.colors.RED)


def reset_example(
    project_path: ProjectPathOption = Path("examples/tiny_vn"),
) -> None:
    """Reset example project metadata/output to a clean baseline for repeatable tests."""
    output_dir = project_path / "output"
    if output_dir.exists():
        rmtree(output_dir)

    metadata_dir = project_path / "metadata"
    if metadata_dir.exists():
        rmtree(metadata_dir)

    # Regenerate from Pydantic models
    typer.echo(f"Regenerating baseline into {project_path}")
    import anyio

    anyio.run(write_baseline, project_path)
    typer.secho(f"Reset {project_path} to baseline data.", fg=typer.colors.GREEN)
