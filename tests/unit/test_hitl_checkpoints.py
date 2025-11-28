"""HITL checkpointer and persistence smoke tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from rentl_agents.hitl.checkpoints import get_default_checkpointer


@pytest.mark.anyio
async def test_get_default_checkpointer_creates_sqlite(tmp_path: Path) -> None:
    """Providing a path should yield a SQLite-backed saver and create the DB."""
    db_path = tmp_path / ".rentl" / "checkpoints.db"
    saver = await get_default_checkpointer(db_path)

    assert isinstance(saver, AsyncSqliteSaver)
    await saver.setup()  # ensure schema initialized
    assert db_path.exists()

    config = {"configurable": {"thread_id": "t1", "checkpoint_ns": "test"}}
    checkpoint = {
        "v": 1,
        "id": "c1",
        "ts": datetime.now(tz=UTC).isoformat(),
        "channel_values": {},
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": [],
    }
    metadata: dict[str, str] = {}
    new_versions: dict[str, str] = {}

    await saver.aput(config, checkpoint, metadata, new_versions)
    restored = await saver.aget(config)

    assert restored is not None
    assert restored["id"] == "c1"

    # Ensure the underlying sqlite connection is closed to avoid thread leaks.
    await saver.conn.close()
