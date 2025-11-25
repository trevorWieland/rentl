"""Checkpointer helpers for HITL-capable LangGraph agents."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


def _ensure_parent(path: Path) -> None:
    """Ensure parent directories exist for the checkpoint database."""
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_sqlite_saver(db_path: Path) -> BaseCheckpointSaver:
    """Return a SQLite-backed checkpointer."""
    _ensure_parent(db_path)
    connection = sqlite3.connect(db_path)
    return SqliteSaver(connection)


def get_default_checkpointer(sqlite_path: str | Path | None = None) -> BaseCheckpointSaver:
    """Return the preferred checkpointer for subagents.

    Args:
        sqlite_path: Optional path to a sqlite database for persistence. If not
            provided, uses the RENTL_CHECKPOINT_DB env var when present. Falls
            back to in-memory saver if no path is specified.
    """
    path: Path | None = None
    if sqlite_path:
        path = Path(sqlite_path)
    else:
        from os import getenv

        db_env = getenv("RENTL_CHECKPOINT_DB")
        if db_env:
            path = Path(db_env)

    if path:
        return _load_sqlite_saver(path)

    logger.info("No checkpoint db specified; using MemorySaver for HITL checkpoints.")
    return MemorySaver()
