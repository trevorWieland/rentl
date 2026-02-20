"""Unit tests for validation entrypoint wrappers."""

from typing import cast
from uuid import UUID

from rentl_schemas.events import ProgressEvent
from rentl_schemas.primitives import JsonValue, PhaseName, PhaseStatus, RunStatus
from rentl_schemas.progress import (
    ProgressPercentMode,
    ProgressTotalStatus,
    ProgressUnit,
)
from rentl_schemas.validation import (
    validate_context_input,
    validate_context_output,
    validate_edit_input,
    validate_edit_output,
    validate_phase_progress,
    validate_pipeline_config,
    validate_pretranslation_input,
    validate_pretranslation_output,
    validate_progress_metric,
    validate_progress_snapshot,
    validate_progress_update,
    validate_project_config,
    validate_qa_input,
    validate_qa_output,
    validate_run_config,
    validate_run_progress,
    validate_translate_input,
    validate_translate_output,
)

U7 = UUID("01945b78-c431-7000-8000-000000000001")

# Test fixture values: JSON primitives plus Pydantic-coercible Python types
type _FixtureValue = (
    str
    | int
    | float
    | bool
    | UUID
    | PhaseName
    | PhaseStatus
    | RunStatus
    | ProgressEvent
    | ProgressPercentMode
    | ProgressUnit
    | ProgressTotalStatus
    | list[_FixtureValue]
    | dict[str, _FixtureValue]
    | None
)


def _p(d: dict[str, _FixtureValue]) -> dict[str, JsonValue]:
    """Coerce test fixture dicts for validator consumption.

    Returns:
        dict[str, JsonValue]: The payload typed for validator consumption.
    """
    return cast(dict[str, JsonValue], d)


def test_validate_project_config() -> None:
    """Validate a minimal project configuration."""
    result = validate_project_config(
        _p({
            "schema_version": {"major": 0, "minor": 1, "patch": 0},
            "project_name": "test",
            "paths": {
                "workspace_dir": "/tmp/ws",
                "input_path": "/tmp/in.csv",
                "output_dir": "/tmp/out",
                "logs_dir": "/tmp/logs",
            },
            "formats": {"input_format": "csv", "output_format": "csv"},
            "languages": {"source_language": "en", "target_languages": ["ja"]},
        })
    )
    assert result.project_name == "test"


def test_validate_pipeline_config() -> None:
    """Validate a minimal pipeline configuration."""
    result = validate_pipeline_config(
        _p({
            "default_model": {"model_id": "test-model"},
            "phases": [{"phase": "context", "agents": ["ctx_agent"]}],
        })
    )
    assert len(result.phases) == 1


def test_validate_run_config() -> None:
    """Validate a minimal run configuration."""
    result = validate_run_config(
        _p({
            "project": {
                "schema_version": {"major": 0, "minor": 1, "patch": 0},
                "project_name": "test",
                "paths": {
                    "workspace_dir": "/tmp/ws",
                    "input_path": "/tmp/in.csv",
                    "output_dir": "/tmp/out",
                    "logs_dir": "/tmp/logs",
                },
                "formats": {"input_format": "csv", "output_format": "csv"},
                "languages": {"source_language": "en", "target_languages": ["ja"]},
            },
            "logging": {"sinks": [{"type": "noop"}]},
            "endpoint": {
                "provider_name": "test",
                "base_url": "https://api.example.com/v1",
                "api_key_env": "TEST_KEY",
            },
            "pipeline": {
                "default_model": {"model_id": "test-model"},
                "phases": [{"phase": "context", "agents": ["ctx_agent"]}],
            },
            "concurrency": {},
            "retry": {},
            "cache": {},
        })
    )
    assert result.project.project_name == "test"


def test_validate_context_input() -> None:
    """Validate context phase input."""
    result = validate_context_input(
        _p({
            "run_id": U7,
            "source_lines": [{"line_id": "line_1", "text": "Hello"}],
        })
    )
    assert len(result.source_lines) == 1


def test_validate_context_output() -> None:
    """Validate context phase output."""
    result = validate_context_output(
        _p({
            "run_id": U7,
            "scene_summaries": [],
            "context_notes": [],
        })
    )
    assert result.run_id == U7


def test_validate_pretranslation_input() -> None:
    """Validate pretranslation phase input."""
    result = validate_pretranslation_input(
        _p({
            "run_id": U7,
            "source_lines": [{"line_id": "line_1", "text": "Hello"}],
        })
    )
    assert len(result.source_lines) == 1


def test_validate_pretranslation_output() -> None:
    """Validate pretranslation phase output."""
    result = validate_pretranslation_output(
        _p({
            "run_id": U7,
            "annotations": [],
            "term_candidates": [],
        })
    )
    assert result.run_id == U7


def test_validate_translate_input() -> None:
    """Validate translate phase input."""
    result = validate_translate_input(
        _p({
            "run_id": U7,
            "target_language": "ja",
            "source_lines": [{"line_id": "line_1", "text": "Hello"}],
        })
    )
    assert result.target_language == "ja"


def test_validate_translate_output() -> None:
    """Validate translate phase output."""
    result = validate_translate_output(
        _p({
            "run_id": U7,
            "target_language": "ja",
            "translated_lines": [{"line_id": "line_1", "text": "Translated"}],
        })
    )
    assert len(result.translated_lines) == 1


def test_validate_qa_input() -> None:
    """Validate QA phase input."""
    result = validate_qa_input(
        _p({
            "run_id": U7,
            "target_language": "ja",
            "source_lines": [{"line_id": "line_1", "text": "Hello"}],
            "translated_lines": [{"line_id": "line_1", "text": "Translated"}],
        })
    )
    assert result.target_language == "ja"


def test_validate_qa_output() -> None:
    """Validate QA phase output."""
    result = validate_qa_output(
        _p({
            "run_id": U7,
            "target_language": "ja",
            "issues": [],
            "summary": {"total_issues": 0, "by_category": {}, "by_severity": {}},
        })
    )
    assert result.summary.total_issues == 0


def test_validate_edit_input() -> None:
    """Validate edit phase input."""
    result = validate_edit_input(
        _p({
            "run_id": U7,
            "target_language": "ja",
            "translated_lines": [{"line_id": "line_1", "text": "Translated"}],
        })
    )
    assert result.target_language == "ja"


def test_validate_edit_output() -> None:
    """Validate edit phase output."""
    result = validate_edit_output(
        _p({
            "run_id": U7,
            "target_language": "ja",
            "edited_lines": [{"line_id": "line_1", "text": "Edited"}],
            "change_log": [],
        })
    )
    assert len(result.edited_lines) == 1


def _phase_progress_dict() -> dict[str, _FixtureValue]:
    """Build a minimal phase progress dict with enum instances.

    Returns:
        dict[str, _FixtureValue]: Minimal PhaseProgress-compatible dict.
    """
    return {
        "phase": PhaseName.TRANSLATE,
        "status": PhaseStatus.PENDING,
        "summary": {"percent_mode": ProgressPercentMode.UNAVAILABLE},
    }


def _run_progress_dict() -> dict[str, _FixtureValue]:
    """Build a minimal run progress dict with enum instances.

    Returns:
        dict[str, _FixtureValue]: Minimal RunProgress-compatible dict.
    """
    return {
        "phases": [_phase_progress_dict()],
        "summary": {"percent_mode": ProgressPercentMode.UNAVAILABLE},
    }


def test_validate_progress_metric() -> None:
    """Validate a progress metric."""
    result = validate_progress_metric(
        _p({
            "metric_key": "lines_translated",
            "unit": ProgressUnit.LINES,
            "completed_units": 0,
            "total_status": ProgressTotalStatus.UNKNOWN,
            "percent_mode": ProgressPercentMode.UNAVAILABLE,
        })
    )
    assert result.metric_key == "lines_translated"


def test_validate_phase_progress() -> None:
    """Validate phase progress."""
    result = validate_phase_progress(_p(_phase_progress_dict()))
    assert result.status == PhaseStatus.PENDING


def test_validate_run_progress() -> None:
    """Validate run progress."""
    result = validate_run_progress(_p(_run_progress_dict()))
    assert len(result.phases) == 1


def test_validate_progress_snapshot() -> None:
    """Validate a progress snapshot."""
    result = validate_progress_snapshot(
        _p({
            "run_id": U7,
            "status": RunStatus.PENDING,
            "progress": _run_progress_dict(),
            "updated_at": "2026-01-01T00:00:00Z",
        })
    )
    assert result.run_id == U7


def test_validate_progress_update() -> None:
    """Validate a progress update."""
    result = validate_progress_update(
        _p({
            "run_id": U7,
            "event": ProgressEvent.RUN_STARTED,
            "timestamp": "2026-01-01T00:00:00Z",
            "run_progress": _run_progress_dict(),
        })
    )
    assert result.event == ProgressEvent.RUN_STARTED
