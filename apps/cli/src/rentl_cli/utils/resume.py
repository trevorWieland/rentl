"""Utilities for resolving resume thread IDs from checkpoint stores."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal
from uuid import uuid4

import typer


def choose_thread_id(
    *,
    prefix: Literal["context", "translate", "edit"],
    resume: bool,
    resume_latest: bool,
    thread_id: str | None,
    no_checkpoint: bool,
    checkpoint_path: Path,
    project_path: Path | None = None,
    route_ids: list[str] | None = None,
) -> str:
    """Resolve the thread id to use for a pipeline run.

    Args:
        prefix: Identifier prefix for new thread ids.
        resume: Whether the user requested resume.
        resume_latest: Whether to resume using the most recent checkpoint thread id.
        thread_id: User-provided thread id, if any.
        no_checkpoint: Whether checkpoint persistence is disabled.
        checkpoint_path: Path to the checkpoint database.
        project_path: Optional project path to read last-run status for resume hints.
        route_ids: Optional route ids used to derive a deterministic thread id when starting new runs.

    Returns:
        str: Resolved thread id for the run.

    Raises:
        typer.Exit: When resume options are invalid or no checkpoint data is available.
    """
    if resume and resume_latest:
        typer.secho("Use either --resume with --thread-id or --resume-latest, not both.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if resume_latest and thread_id:
        typer.secho("--resume-latest cannot be combined with --thread-id.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if (resume or resume_latest) and no_checkpoint:
        typer.secho("Resume flags cannot be combined with --no-checkpoint.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if resume and not thread_id:
        typer.secho("Provide --thread-id when using --resume to continue a prior run.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if resume_latest:
        if project_path:
            from rentl_cli.utils.status_snapshot import _get_phase_snapshot, load_phase_status

            status = load_phase_status(project_path)
            snapshot = _get_phase_snapshot(status, prefix) if status else None
            if snapshot and route_ids:
                if snapshot.route_scope and snapshot.route_scope == sorted(route_ids):
                    return snapshot.thread_id
                if snapshot.route_scope and snapshot.route_scope != sorted(route_ids):
                    typer.secho(
                        "Latest run used different route filters; specify --thread-id or rerun without --resume-latest.",
                        fg=typer.colors.RED,
                    )
                    raise typer.Exit(code=1)
            if snapshot and not route_ids:
                return snapshot.thread_id
        latest = _read_latest_thread_id(checkpoint_path)
        if latest is None:
            typer.secho("No checkpoint found to resume from. Run without --resume-latest first.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        return latest

    if thread_id:
        return thread_id

    if route_ids:
        return f"{prefix}-routes-{','.join(sorted(route_ids))}"

    return f"{prefix}-{uuid4()}"


def _read_latest_thread_id(checkpoint_path: Path) -> str | None:
    """Return the most recent thread_id from the checkpoint database, if present."""
    if not checkpoint_path.exists():
        return None

    try:
        conn = sqlite3.connect(checkpoint_path)
        try:
            cursor = conn.execute("SELECT thread_id FROM checkpoints ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            return str(row[0]) if row else None
        finally:
            conn.close()
    except sqlite3.Error:
        return None
