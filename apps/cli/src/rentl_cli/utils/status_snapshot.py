"""Helpers for persisting last-run status per pipeline phase."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import orjson
from pydantic import BaseModel, Field, ValidationError


class PhaseFailure(BaseModel):
    """Failure details for a specific entity."""

    stage: str = Field(description="Pipeline stage that failed (e.g., translate_scene).")
    entity_id: str = Field(description="Identifier for the entity (scene/character/etc).")
    error: str = Field(description="Error message.")


class PhaseProgress(BaseModel):
    """Progress metadata for a phase run."""

    total_items: int | None = Field(default=None, description="Total work items planned.")
    completed_items: int = Field(default=0, description="Work items completed.")
    skipped_items: int | None = Field(default=None, description="Work items skipped.")
    progress_pct: float | None = Field(default=None, description="Completion percent.")
    elapsed_seconds: float | None = Field(default=None, description="Elapsed seconds since start.")
    estimated_total_seconds: float | None = Field(default=None, description="Estimated total duration.")
    estimated_remaining_seconds: float | None = Field(default=None, description="Estimated time remaining.")


class PhaseSnapshot(BaseModel):
    """Compact metadata about the last run of a pipeline phase."""

    thread_id: str = Field(description="Thread id used for the run.")
    status: Literal["ok", "error"] = Field(description="Whether the run completed without recorded errors.")
    state: Literal["running", "completed"] = Field(description="Current state of the run.")
    mode: str | None = Field(default=None, description="Processing mode used for the run.")
    route_scope: list[str] | None = Field(default=None, description="Route ids targeted for the run, if any.")
    updated_at: datetime = Field(description="Timestamp when the snapshot was recorded.")
    started_at: datetime | None = Field(default=None, description="Start timestamp.")
    finished_at: datetime | None = Field(default=None, description="Finish timestamp.")
    details: dict[str, int | float] | None = Field(
        default=None, description="Phase-specific counters (scenes, lines, skips, etc.)."
    )
    errors: list[str] = Field(default_factory=list, description="Stringified errors for user display.")
    failures: list[PhaseFailure] = Field(default_factory=list, description="Per-entity failure details.")
    progress: PhaseProgress | None = Field(default=None, description="Progress metrics for the run.")


class StatusFile(BaseModel):
    """Status entries keyed by phase."""

    context: PhaseSnapshot | None = None
    translate: PhaseSnapshot | None = None
    edit: PhaseSnapshot | None = None


def _get_phase_snapshot(
    status: StatusFile | None, phase: Literal["context", "translate", "edit"]
) -> PhaseSnapshot | None:
    """Return a snapshot for a given phase."""
    if status is None:
        return None
    if phase == "context":
        return status.context
    if phase == "translate":
        return status.translate
    return status.edit


def _set_phase_snapshot(
    status: StatusFile, phase: Literal["context", "translate", "edit"], snapshot: PhaseSnapshot
) -> None:
    """Assign a snapshot for a given phase."""
    if phase == "context":
        status.context = snapshot
    elif phase == "translate":
        status.translate = snapshot
    else:
        status.edit = snapshot


def _status_path(project_path: Path) -> Path:
    return project_path / ".rentl" / "status.json"


def _load_status(status_path: Path) -> StatusFile | None:
    if not status_path.exists():
        return None
    try:
        payload = orjson.loads(status_path.read_bytes())
        return StatusFile.model_validate(payload)
    except (OSError, orjson.JSONDecodeError, ValidationError):
        return None


def _write_status(status_path: Path, status: StatusFile) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_bytes(orjson.dumps(status.model_dump(mode="json"), option=orjson.OPT_INDENT_2))


def record_phase_snapshot(
    project_path: Path,
    phase: Literal["context", "translate", "edit"],
    *,
    thread_id: str,
    mode: str | None,
    details: dict[str, int | float] | None,
    errors: list[str],
    failures: list[PhaseFailure] | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    progress: PhaseProgress | None = None,
    route_ids: list[str] | None = None,
) -> None:
    """Persist snapshot for a phase run.

    Note:
        This function writes to disk; callers should avoid frequent calls in hot loops.
    """
    status_path = _status_path(project_path)
    current = _load_status(status_path) or StatusFile()
    finished_at = finished_at or datetime.now(UTC)
    started_at = started_at or finished_at
    snapshot = PhaseSnapshot(
        thread_id=thread_id,
        status="error" if errors else "ok",
        state="completed",
        mode=mode,
        route_scope=sorted(route_ids) if route_ids else None,
        updated_at=finished_at,
        started_at=started_at,
        finished_at=finished_at,
        details=details,
        errors=errors,
        failures=failures or [],
        progress=progress,
    )
    _set_phase_snapshot(current, phase, snapshot)
    _write_status(status_path, current)


def latest_thread_id_from_status(project_path: Path, phase: Literal["context", "translate", "edit"]) -> str | None:
    """Return the most recent thread id for a phase, if recorded."""
    status_path = _status_path(project_path)
    status = _load_status(status_path)
    if not status:
        return None
    snapshot = _get_phase_snapshot(status, phase)
    return snapshot.thread_id if snapshot else None


def load_phase_status(project_path: Path) -> StatusFile | None:
    """Return the current status file content if present."""
    return _load_status(_status_path(project_path))


def record_phase_start(
    project_path: Path,
    phase: Literal["context", "translate", "edit"],
    *,
    thread_id: str,
    mode: str | None,
    total_items: int | None = None,
    route_ids: list[str] | None = None,
) -> None:
    """Persist a running snapshot before starting a phase."""
    status_path = _status_path(project_path)
    current = _load_status(status_path) or StatusFile()
    progress = PhaseProgress(
        total_items=total_items,
        completed_items=0,
        skipped_items=0,
        progress_pct=0.0 if total_items else None,
        elapsed_seconds=0.0,
        estimated_total_seconds=None,
        estimated_remaining_seconds=None,
    )
    snapshot = PhaseSnapshot(
        thread_id=thread_id,
        status="ok",
        state="running",
        mode=mode,
        route_scope=sorted(route_ids) if route_ids else None,
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        finished_at=None,
        details=None,
        errors=[],
        failures=[],
        progress=progress,
    )
    _set_phase_snapshot(current, phase, snapshot)
    _write_status(status_path, current)
