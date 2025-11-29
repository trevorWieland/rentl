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
) -> str:
    """Resolve the thread id to use for a pipeline run.

    Args:
        prefix: Identifier prefix for new thread ids.
        resume: Whether the user requested resume.
        resume_latest: Whether to resume using the most recent checkpoint thread id.
        thread_id: User-provided thread id, if any.
        no_checkpoint: Whether checkpoint persistence is disabled.
        checkpoint_path: Path to the checkpoint database.

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
        latest = _read_latest_thread_id(checkpoint_path)
        if latest is None:
            typer.secho("No checkpoint found to resume from. Run without --resume-latest first.", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        return latest

    if thread_id:
        return thread_id

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
