"""Checkpointer helpers for HITL-capable LangGraph agents."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import anyio
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from rentl_core.util.logging import get_logger

logger = get_logger(__name__)


async def _load_sqlite_saver(db_path: Path) -> BaseCheckpointSaver:
    """Return an async SQLite-backed checkpointer."""
    await anyio.Path(db_path.parent).mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(db_path)
    return AsyncSqliteSaver(connection)


async def get_default_checkpointer(sqlite_path: str | Path | None = None) -> BaseCheckpointSaver:
    """Return the preferred checkpointer for subagents (async-only).

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
        return await _load_sqlite_saver(path)

    logger.info("No checkpoint db specified; using MemorySaver for HITL checkpoints.")
    return MemorySaver()


async def maybe_close_checkpointer(checkpointer: BaseCheckpointSaver) -> None:
    """Close sqlite-backed checkpointers to avoid hanging interpreter shutdown.

    Args:
        checkpointer: The checkpointer to close if it owns a sqlite connection.
    """
    # AsyncSqliteSaver exposes the underlying connection as ``conn``.
    conn = getattr(checkpointer, "conn", None)
    if conn is not None:
        close = getattr(conn, "close", None)
        if callable(close):
            await close()
