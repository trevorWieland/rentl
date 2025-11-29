"""Tests for CLI resume helper utilities."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import typer
from rentl_cli.utils.resume import _read_latest_thread_id, choose_thread_id
from rentl_cli.utils.status_snapshot import record_phase_snapshot


def _seed_checkpoint(db_path: Path, thread_ids: list[str]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints (thread_id TEXT, checkpoint_id TEXT, checkpoint_ns TEXT, type TEXT, checkpoint BLOB)"
        )
        for idx, tid in enumerate(thread_ids):
            conn.execute(
                "INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint_ns, type, checkpoint) VALUES (?, ?, ?, ?, ?)",
                (tid, f"c{idx}", "default", "stub", b"{}"),
            )
        conn.commit()
    finally:
        conn.close()


def test_read_latest_thread_id(tmp_path: Path) -> None:
    """Should return latest thread id by insertion order or None when missing."""
    db_path = tmp_path / "checkpoints.db"
    _seed_checkpoint(db_path, ["tid-1", "tid-2"])

    latest = _read_latest_thread_id(db_path)
    assert latest == "tid-2"

    missing = _read_latest_thread_id(tmp_path / "missing.db")
    assert missing is None


def test_choose_thread_id_resume_latest(tmp_path: Path) -> None:
    """Resume latest chooses most recent thread id from checkpoint DB."""
    db_path = tmp_path / "checkpoints.db"
    _seed_checkpoint(db_path, ["tid-1", "tid-2", "tid-3"])

    tid = choose_thread_id(
        prefix="edit",
        resume=False,
        resume_latest=True,
        thread_id=None,
        no_checkpoint=False,
        checkpoint_path=db_path,
    )
    assert tid == "tid-3"


def test_choose_thread_id_conflicts_raise(tmp_path: Path) -> None:
    """Invalid resume combinations should exit with code 1."""
    db_path = tmp_path / "checkpoints.db"
    _seed_checkpoint(db_path, ["tid-1"])

    with pytest.raises(typer.Exit):
        choose_thread_id(
            prefix="edit",
            resume=True,
            resume_latest=True,
            thread_id=None,
            no_checkpoint=False,
            checkpoint_path=db_path,
        )

    with pytest.raises(typer.Exit):
        choose_thread_id(
            prefix="edit",
            resume_latest=True,
            resume=False,
            thread_id="tid-explicit",
            no_checkpoint=False,
            checkpoint_path=db_path,
        )

    with pytest.raises(typer.Exit):
        choose_thread_id(
            prefix="edit",
            resume=True,
            resume_latest=False,
            thread_id=None,
            no_checkpoint=True,
            checkpoint_path=db_path,
        )


def test_choose_thread_id_generates_when_no_resume(tmp_path: Path) -> None:
    """Without resume flags, a new thread id should be generated."""
    tid = choose_thread_id(
        prefix="translate",
        resume=False,
        resume_latest=False,
        thread_id=None,
        no_checkpoint=False,
        checkpoint_path=tmp_path / "checkpoints.db",
    )
    assert tid.startswith("translate-")


def test_choose_thread_id_uses_routes_when_provided(tmp_path: Path) -> None:
    """When route ids are provided, thread id should be deterministic."""
    tid = choose_thread_id(
        prefix="translate",
        resume=False,
        resume_latest=False,
        thread_id=None,
        no_checkpoint=False,
        checkpoint_path=tmp_path / "checkpoints.db",
        route_ids=["b", "a"],
    )
    assert tid == "translate-routes-a,b"


def test_choose_thread_id_prefers_status_snapshot(tmp_path: Path) -> None:
    """When --resume-latest is used, prefer status snapshot thread ids."""
    record_phase_snapshot(
        tmp_path,
        "translate",
        thread_id="tid-from-status",
        mode="gap-fill",
        details=None,
        errors=[],
        route_ids=["r1", "r2"],
    )

    tid = choose_thread_id(
        prefix="translate",
        resume=False,
        resume_latest=True,
        thread_id=None,
        no_checkpoint=False,
        checkpoint_path=tmp_path / "checkpoints.db",
        project_path=tmp_path,
        route_ids=["r1", "r2"],
    )
    assert tid == "tid-from-status"


def test_choose_thread_id_route_mismatch_errors(tmp_path: Path) -> None:
    """Route mismatch with resume-latest should raise."""
    record_phase_snapshot(
        tmp_path,
        "translate",
        thread_id="tid-from-status",
        mode="gap-fill",
        details=None,
        errors=[],
        route_ids=["r1", "r2"],
    )

    with pytest.raises(typer.Exit):
        choose_thread_id(
            prefix="translate",
            resume=False,
            resume_latest=True,
            thread_id=None,
            no_checkpoint=False,
            checkpoint_path=tmp_path / "checkpoints.db",
            project_path=tmp_path,
            route_ids=["r3"],
        )
