"""Tests for CLI status snapshot utilities and resume helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import typer
from rentl_cli.utils.resume import choose_thread_id
from rentl_cli.utils.status_snapshot import (
    PhaseProgress,
    latest_thread_id_from_status,
    load_phase_status,
    record_phase_snapshot,
    record_phase_start,
)


def _status_path(tmp_path: Path) -> Path:
    return tmp_path / ".rentl" / "status.json"


def test_record_phase_start_and_snapshot(tmp_path: Path) -> None:
    """record_phase_start/record_phase_snapshot should write and load snapshots."""
    project_path = tmp_path
    record_phase_start(project_path, "context", thread_id="ctx-1", mode="gap-fill", total_items=5)
    status = load_phase_status(project_path)
    assert status is not None
    assert status.context is not None
    assert status.context.state == "running"
    assert status.context.progress is not None
    assert status.context.progress.total_items == 5

    record_phase_snapshot(
        project_path,
        "context",
        thread_id="ctx-1",
        mode="overwrite",
        details={"done": 5},
        errors=["err1"],
        failures=[],
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        progress=PhaseProgress(total_items=5, completed_items=5, skipped_items=0, progress_pct=100.0),
        route_ids=["route_a"],
    )
    status_done = load_phase_status(project_path)
    assert status_done is not None
    assert status_done.context is not None
    assert status_done.context.state == "completed"
    assert status_done.context.status == "error"  # errors were present
    assert status_done.context.route_scope == ["route_a"]

    latest = latest_thread_id_from_status(project_path, "context")
    assert latest == "ctx-1"


def test_choose_thread_id_invalid_flags(tmp_path: Path) -> None:
    """Invalid resume flag combos should exit with code 1."""
    checkpoint = tmp_path / ".rentl" / "checkpoints.db"
    with pytest.raises((SystemExit, typer.Exit)):
        choose_thread_id(
            prefix="context",
            resume=True,
            resume_latest=True,
            thread_id=None,
            no_checkpoint=False,
            checkpoint_path=checkpoint,
        )

    with pytest.raises((SystemExit, typer.Exit)):
        choose_thread_id(
            prefix="translate",
            resume=True,
            resume_latest=False,
            thread_id=None,
            no_checkpoint=True,
            checkpoint_path=checkpoint,
        )

    with pytest.raises((SystemExit, typer.Exit)):
        choose_thread_id(
            prefix="edit",
            resume=True,
            resume_latest=False,
            thread_id=None,
            no_checkpoint=False,
            checkpoint_path=checkpoint,
        )


def test_choose_thread_id_resume_latest_with_routes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Resume latest should use status file when route scopes match."""
    checkpoint = tmp_path / ".rentl" / "checkpoints.db"
    status_path = _status_path(tmp_path)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    record_phase_snapshot(
        tmp_path,
        "context",
        thread_id="ctx-routes-1",
        mode="gap-fill",
        details=None,
        errors=[],
        route_ids=["a", "b"],
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        progress=None,
    )

    thread_id = choose_thread_id(
        prefix="context",
        resume=False,
        resume_latest=True,
        thread_id=None,
        no_checkpoint=False,
        checkpoint_path=checkpoint,
        project_path=tmp_path,
        route_ids=["a", "b"],
    )
    assert thread_id == "ctx-routes-1"

    # Mismatched route scope should error
    with pytest.raises((SystemExit, typer.Exit)):
        choose_thread_id(
            prefix="context",
            resume=False,
            resume_latest=True,
            thread_id=None,
            no_checkpoint=False,
            checkpoint_path=checkpoint,
            project_path=tmp_path,
            route_ids=["c"],
        )
