"""CLI commands for running pipelines."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from shutil import rmtree
from typing import Annotated, Any, Literal, cast
from uuid import uuid4

import typer
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

from rentl_cli.cli_types import ProjectPathOption
from rentl_cli.utils.baseline import write_baseline


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


def _progress_printer(verbose: bool) -> Callable[[str, str], None] | None:
    """Return a progress callback that logs events when verbose is enabled."""
    if not verbose:
        return None

    def _cb(event: str, entity: str) -> None:
        typer.echo(f"[progress] {event} :: {entity}")

    return _cb


async def _collect_progress_snapshot(context: ProjectContext) -> dict[str, Any]:
    """Compute translation/editing progress for public-facing sharing.

    Returns:
        dict[str, object]: Progress snapshot with overall and per-route percentages.
    """
    total_lines = 0
    translated_lines = 0
    checked_lines = 0
    total_issues = 0
    routes_payload: list[dict[str, object]] = []

    for sid in context.scenes:
        lines = await context.load_scene_lines(sid)
        total_lines += len(lines)
        await context._load_translations(sid)
        translations = await context.get_translations(sid)
        translated_lines += len(translations)
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
            {
                "route_id": route.id,
                "total_lines": route_lines,
                "translated_lines": route_translated,
                "checked_lines": route_checked,
                "failing_checks": route_issues,
                "translation_progress_pct": round((route_translated / route_lines * 100) if route_lines else 0.0, 1),
                "editing_progress_pct": round((route_checked / route_translated * 100) if route_translated else 0.0, 1),
            }
        )

    translation_progress = (translated_lines / total_lines * 100) if total_lines else 0.0
    editing_progress = (checked_lines / translated_lines * 100) if translated_lines else 0.0

    checkpoint_path = context.project_path / ".rentl" / "checkpoints.db"
    checkpoint_info: dict[str, str] | None = None
    if checkpoint_path.exists():
        from datetime import datetime

        mtime = checkpoint_path.stat().st_mtime
        checkpoint_info = {"path": str(checkpoint_path), "modified": datetime.fromtimestamp(mtime).isoformat()}

    return {
        "translation_progress_pct": round(translation_progress, 1),
        "editing_progress_pct": round(editing_progress, 1),
        "total_lines": total_lines,
        "translated_lines": translated_lines,
        "checked_lines": checked_lines,
        "failing_checks": total_issues,
        "routes": routes_payload,
        "checkpoint": checkpoint_info,
        "thread_id_hints": ["context-<uuid>", "translate-<uuid>", "edit-<uuid>"],
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


def _print_top_issues(report_path: str) -> None:
    """Pretty-print top issues from the editor report if present."""
    try:
        import orjson

        data = orjson.loads(Path(report_path).read_bytes())
    except Exception:
        return

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
        scenes = context.scenes.values()
        characters = context.characters.values()
        locations = context.locations.values()
        routes = context.routes.values()

        scenes_incomplete = _filter_scenes(scenes, "gap-fill")
        characters_incomplete = _filter_characters(characters, "gap-fill")
        locations_incomplete = _filter_locations(locations, "gap-fill")
        routes_incomplete = _filter_routes(routes, "gap-fill")

        if not public_only:
            typer.secho("Status", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"  Scenes: {len(scenes)} total / {len(scenes_incomplete)} incomplete")
            typer.echo(f"  Characters: {len(characters)} total / {len(characters_incomplete)} incomplete")
            typer.echo(f"  Locations: {len(locations)} total / {len(locations_incomplete)} incomplete")
            typer.echo(f"  Routes: {len(routes)} total / {len(routes_incomplete)} incomplete")
            typer.echo(
                f"  Translation Progress: {progress['translation_progress_pct']:.1f}% "
                f"({progress['translated_lines']}/{progress['total_lines']} lines)"
            )
            typer.echo(
                f"  Editing Progress: {progress['editing_progress_pct']:.1f}% "
                f"({progress['checked_lines']}/{progress['translated_lines']} translated lines)"
            )
            typer.echo(f"  Failing Checks: {progress.get('failing_checks', 0)}")

        if by_route and not public_only:
            typer.secho("\n  By Route:", fg=typer.colors.CYAN, bold=True)
            routes_progress = cast(list[dict[str, object]], progress.get("routes", []))
            for route in routes_progress:
                t_pct = route["translation_progress_pct"]
                e_pct = route["editing_progress_pct"]
                route_lines = route["total_lines"]
                route_translated = route["translated_lines"]
                route_checked = route["checked_lines"]
                failing = route.get("failing_checks", 0)
                typer.echo(
                    f"    {route['route_id']}: translate {t_pct:.1f}% ({route_translated}/{route_lines}), "
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

        if snapshot_json or public_only:
            if not public_only:
                typer.echo("\nPublic progress snapshot (JSON):")
            typer.echo(json.dumps(progress, indent=2))

    typer.echo("Collecting project status...")
    import anyio

    anyio.run(_status_async, project_path)


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
    no_checkpoint: Annotated[bool, typer.Option("--no-checkpoint", help="Disable checkpoint persistence.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Context Builder pipeline to enrich all game metadata."""
    configure_logging(verbose)
    typer.secho("Starting Context Builder pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = thread_id or f"context-{uuid4()}"
    result = run_context_builder(
        project_path,
        allow_overwrite=overwrite,
        mode=mode,
        scene_ids=scene_ids or None,
        route_ids=route_ids or None,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
        progress_cb=_progress_printer(verbose),
        checkpoint_enabled=not no_checkpoint,
    )

    # Display results
    typer.secho("\nContext Builder Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes detailed: {result.scenes_detailed}")
    typer.echo(f"  Characters detailed: {result.characters_detailed}")
    typer.echo(f"  Locations detailed: {result.locations_detailed}")
    typer.echo(f"  Glossary entries added: {result.glossary_entries_added}")
    typer.echo(f"  Glossary entries updated: {result.glossary_entries_updated}")
    typer.echo(f"  Routes detailed: {result.routes_detailed}")
    typer.echo(f"  Resume thread id: {thread_id}")
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
    no_checkpoint: Annotated[bool, typer.Option("--no-checkpoint", help="Disable checkpoint persistence.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Translator pipeline to translate scenes."""
    configure_logging(verbose)
    typer.secho("Starting Translator pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = thread_id or f"translate-{uuid4()}"
    result = run_translator(
        project_path,
        scene_ids=scene_ids or None,
        route_ids=route_ids or None,
        allow_overwrite=overwrite,
        mode=mode,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
        progress_cb=_progress_printer(verbose),
        checkpoint_enabled=not no_checkpoint,
    )

    # Display results
    typer.secho("\nTranslator Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes translated: {result.scenes_translated}")
    typer.echo(f"  Lines translated: {result.lines_translated}")
    typer.echo(f"  Scenes skipped: {result.scenes_skipped}")
    typer.echo(f"  Resume thread id: {thread_id}")
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
    no_checkpoint: Annotated[bool, typer.Option("--no-checkpoint", help="Disable checkpoint persistence.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Enable verbose logging.")] = False,
) -> None:
    """Run the Editor pipeline to perform QA on translations."""
    configure_logging(verbose)
    typer.secho("Starting Editor pipeline...", fg=typer.colors.CYAN, bold=True)

    thread_id = thread_id or f"edit-{uuid4()}"
    result = run_editor(
        project_path,
        scene_ids=scene_ids or None,
        route_ids=route_ids or None,
        mode=mode,
        concurrency=concurrency,
        decision_handler=_prompt_decisions,
        thread_id=thread_id,
        progress_cb=_progress_printer(verbose),
        checkpoint_enabled=not no_checkpoint,
    )

    typer.secho("\nEditor Complete!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  Scenes checked: {result.scenes_checked}")
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
