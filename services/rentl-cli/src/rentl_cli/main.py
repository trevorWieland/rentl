"""CLI entry point - thin adapter over rentl-core."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import tomllib
from dataclasses import replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import NamedTuple, TypeVar
from uuid import UUID, uuid7

import typer
from dotenv import load_dotenv
from pydantic import ValidationError
from rich import print as rprint
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from rentl_agents.wiring import build_agent_pools
from rentl_core import VERSION, AgentTelemetryEmitter, build_status_result
from rentl_core.llm.connection import build_connection_plan, validate_connections
from rentl_core.orchestrator import (
    PipelineOrchestrator,
    PipelineRunContext,
    hydrate_run_context,
)
from rentl_core.ports.export import ExportBatchError, ExportError, ExportResult
from rentl_core.ports.ingest import IngestBatchError, IngestError
from rentl_core.ports.orchestrator import (
    LogSinkProtocol,
    OrchestrationError,
    ProgressSinkProtocol,
)
from rentl_core.ports.storage import StorageBatchError, StorageError
from rentl_io import write_output
from rentl_io.export.router import get_export_adapter
from rentl_io.ingest.router import get_ingest_adapter
from rentl_io.storage.filesystem import (
    FileSystemArtifactStore,
    FileSystemLogStore,
    FileSystemRunStateStore,
)
from rentl_io.storage.log_sink import build_log_sink
from rentl_io.storage.progress_sink import FileSystemProgressSink
from rentl_llm import OpenAICompatibleRuntime
from rentl_schemas.config import (
    LanguageConfig,
    LoggingConfig,
    LogSinkConfig,
    ModelSettings,
    RunConfig,
)
from rentl_schemas.events import (
    CommandCompletedData,
    CommandEvent,
    CommandFailedData,
    CommandStartedData,
    ProgressEvent,
)
from rentl_schemas.io import ExportTarget, IngestSource, TranslatedLine
from rentl_schemas.llm import LlmConnectionReport, LlmEndpointTarget
from rentl_schemas.logs import LogEntry
from rentl_schemas.pipeline import PhaseRunRecord, RunState
from rentl_schemas.primitives import (
    PIPELINE_PHASE_ORDER,
    FileFormat,
    JsonValue,
    LanguageCode,
    LogLevel,
    LogSinkType,
    PhaseName,
    RunId,
    RunStatus,
    UntranslatedPolicy,
)
from rentl_schemas.progress import (
    AgentStatus,
    PhaseProgress,
    ProgressMetric,
    ProgressSummary,
    ProgressUpdate,
    RunProgress,
)
from rentl_schemas.responses import (
    ApiResponse,
    ErrorResponse,
    MetaInfo,
    RunExecutionResult,
    RunStatusResult,
)
from rentl_schemas.results import PhaseResultMetric, ResultMetricUnit
from rentl_schemas.storage import LogFileReference, StorageBackend, StorageReference
from rentl_schemas.validation import validate_run_config

INPUT_OPTION = typer.Option(
    ..., "--input", "-i", help="JSONL file of TranslatedLine records"
)
OUTPUT_OPTION = typer.Option(
    ..., "--output", "-o", help="Path to write exported output"
)
FORMAT_OPTION = typer.Option(..., "--format", "-f", help="Output file format")
UNTRANSLATED_POLICY_OPTION = typer.Option(
    UntranslatedPolicy.ERROR,
    "--untranslated-policy",
    help="Policy for untranslated lines (error|warn|allow)",
)
INCLUDE_SOURCE_TEXT_OPTION = typer.Option(
    False, "--include-source-text", help="Include source_text column in CSV"
)
INCLUDE_SCENE_ID_OPTION = typer.Option(
    False, "--include-scene-id", help="Include scene_id column in CSV"
)
INCLUDE_SPEAKER_OPTION = typer.Option(
    False, "--include-speaker", help="Include speaker column in CSV"
)
COLUMN_ORDER_OPTION = typer.Option(
    None, "--column-order", help="Explicit CSV column order (repeatable)"
)
EXPECTED_LINE_COUNT_OPTION = typer.Option(
    None,
    "--expected-line-count",
    help="Optional expected line count for export audit",
)

CONFIG_OPTION = typer.Option(
    Path("rentl.toml"),
    "--config",
    "-c",
    help="Path to rentl TOML config",
)
RUN_ID_OPTION = typer.Option(
    None, "--run-id", help="Run identifier to resume or continue"
)
PHASE_OPTION = typer.Option(..., "--phase", help="Phase to run")
TARGET_LANGUAGE_OPTION = typer.Option(
    None, "--target-language", "-t", help="Target language code (repeatable)"
)
TARGET_LANGUAGE_SINGLE_OPTION = typer.Option(
    None, "--target-language", "-t", help="Target language code"
)
INPUT_PATH_OPTION = typer.Option(
    None, "--input-path", help="Override input path for ingest"
)
OUTPUT_PATH_OPTION = typer.Option(
    None, "--output-path", help="Override output path for export"
)

app = typer.Typer(
    help="Agentic localization pipeline",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Rentl CLI."""


@app.command()
def version() -> None:
    """Display version information."""
    rprint(f"[bold]rentl[/bold] v{VERSION}")


@app.command("validate-connection")
def validate_connection(
    config_path: Path = CONFIG_OPTION,
) -> None:
    """Validate connectivity for configured model endpoints."""
    command_run_id = uuid7()
    log_sink: LogSinkProtocol | None = None
    try:
        config = _load_resolved_config(config_path)
        log_sink = _build_command_log_sink(config)
        args: dict[str, JsonValue] = {"config_path": str(config_path)}
        _emit_command_log_sync(
            log_sink,
            _build_command_started_log(
                timestamp=_now_timestamp(),
                run_id=command_run_id,
                command="validate-connection",
                args=args,
            ),
        )
        result = asyncio.run(
            _validate_connection_async(
                config=config,
            )
        )
        _emit_command_log_sync(
            log_sink,
            _build_command_completed_log(
                timestamp=_now_timestamp(),
                run_id=command_run_id,
                command="validate-connection",
            ),
        )
        response: ApiResponse[LlmConnectionReport] = ApiResponse(
            data=result,
            error=None,
            meta=MetaInfo(timestamp=_now_timestamp()),
        )
    except Exception as exc:
        error = _error_from_exception(exc)
        if log_sink is not None:
            _emit_command_log_sync(
                log_sink,
                _build_command_failed_log(
                    timestamp=_now_timestamp(),
                    run_id=command_run_id,
                    command="validate-connection",
                    error=error,
                ),
            )
        response = _error_response(error)
    print(response.model_dump_json())


@app.command()
def export(
    config_path: Path = CONFIG_OPTION,
    input_path: Path = INPUT_OPTION,
    output_path: Path = OUTPUT_OPTION,
    format: FileFormat = FORMAT_OPTION,
    untranslated_policy: UntranslatedPolicy = UNTRANSLATED_POLICY_OPTION,
    include_source_text: bool = INCLUDE_SOURCE_TEXT_OPTION,
    include_scene_id: bool = INCLUDE_SCENE_ID_OPTION,
    include_speaker: bool = INCLUDE_SPEAKER_OPTION,
    column_order: list[str] | None = COLUMN_ORDER_OPTION,
    expected_line_count: int | None = EXPECTED_LINE_COUNT_OPTION,
) -> None:
    """Export translated lines to CSV/JSONL/TXT."""
    command_run_id = uuid7()
    log_sink: LogSinkProtocol | None = None
    try:
        config = _load_resolved_config(config_path)
        log_sink = _build_command_log_sink(config)
        args: dict[str, JsonValue] = {
            "config_path": str(config_path),
            "input_path": str(input_path),
            "output_path": str(output_path),
            "format": format.value,
            "untranslated_policy": untranslated_policy.value,
            "include_source_text": include_source_text,
            "include_scene_id": include_scene_id,
            "include_speaker": include_speaker,
            "column_order": _as_json_list(column_order),
            "expected_line_count": expected_line_count,
        }
        _emit_command_log_sync(
            log_sink,
            _build_command_started_log(
                timestamp=_now_timestamp(),
                run_id=command_run_id,
                command="export",
                args=args,
            ),
        )
        result = asyncio.run(
            _export_async(
                input_path=input_path,
                output_path=output_path,
                format=format,
                untranslated_policy=untranslated_policy,
                column_order=column_order,
                include_source_text=include_source_text,
                include_scene_id=include_scene_id,
                include_speaker=include_speaker,
                expected_line_count=expected_line_count,
            )
        )
        _emit_command_log_sync(
            log_sink,
            _build_command_completed_log(
                timestamp=_now_timestamp(),
                run_id=command_run_id,
                command="export",
            ),
        )
        response: ApiResponse[ExportResult] = ApiResponse(
            data=result, error=None, meta=MetaInfo(timestamp=_now_timestamp())
        )
    except ExportBatchError as exc:
        error = _summarize_batch_error(
            exc.errors[0].to_error_response(), len(exc.errors), "export"
        )
        if log_sink is not None:
            _emit_command_log_sync(
                log_sink,
                _build_command_failed_log(
                    timestamp=_now_timestamp(),
                    run_id=command_run_id,
                    command="export",
                    error=error,
                ),
            )
        response = _error_response(error)
    except ExportError as exc:
        error = exc.info.to_error_response()
        if log_sink is not None:
            _emit_command_log_sync(
                log_sink,
                _build_command_failed_log(
                    timestamp=_now_timestamp(),
                    run_id=command_run_id,
                    command="export",
                    error=error,
                ),
            )
        response = _error_response(error)
    except ValueError as exc:
        error = ErrorResponse(code="validation_error", message=str(exc), details=None)
        if log_sink is not None:
            _emit_command_log_sync(
                log_sink,
                _build_command_failed_log(
                    timestamp=_now_timestamp(),
                    run_id=command_run_id,
                    command="export",
                    error=error,
                ),
            )
        response = _error_response(error)
    except Exception as exc:
        error = _error_from_exception(exc)
        if log_sink is not None:
            _emit_command_log_sync(
                log_sink,
                _build_command_failed_log(
                    timestamp=_now_timestamp(),
                    run_id=command_run_id,
                    command="export",
                    error=error,
                ),
            )
        response = _error_response(error)

    print(response.model_dump_json())


@app.command("run-pipeline")
def run_pipeline(
    config_path: Path = CONFIG_OPTION,
    run_id: str | None = RUN_ID_OPTION,
    target_languages: list[str] | None = TARGET_LANGUAGE_OPTION,
) -> None:
    """Run the full pipeline plan.

    Raises:
        typer.Exit: When the run fails in interactive mode.
    """
    command_run_id = uuid7()
    log_sink: LogSinkProtocol | None = None
    progress: Progress | None = None
    console: Console | None = None
    try:
        config = _load_resolved_config(config_path)
        resolved_run_id = _resolve_run_id(run_id)
        command_run_id = resolved_run_id
        bundle = _build_storage_bundle(
            config, resolved_run_id, allow_console_logs=False
        )
        interactive = _should_render_progress()
        if interactive:
            console = Console(stderr=True)
            progress = _build_progress(console)
            reporter = _ProgressReporter(bundle.progress_sink, progress, console)
            bundle = _StorageBundle(
                run_state_store=bundle.run_state_store,
                artifact_store=bundle.artifact_store,
                log_store=bundle.log_store,
                log_sink=bundle.log_sink,
                progress_sink=reporter,
                progress_path=bundle.progress_path,
            )
        log_sink = bundle.log_sink
        args: dict[str, JsonValue] = {
            "config_path": str(config_path),
            "run_id": str(resolved_run_id),
            "target_languages": _as_json_list(target_languages),
        }
        _emit_command_log_sync(
            log_sink,
            _build_command_started_log(
                timestamp=_now_timestamp(),
                run_id=command_run_id,
                command="run-pipeline",
                args=args,
            ),
        )
        if interactive:
            _render_run_start(
                run_id=resolved_run_id,
                phases=_resolve_enabled_phases(config),
                config=config,
                console=console,
            )
        if progress is not None:
            with progress:
                result = asyncio.run(
                    _run_pipeline_async(
                        config=config,
                        bundle=bundle,
                        run_id=resolved_run_id,
                        target_languages=target_languages,
                    )
                )
        else:
            result = asyncio.run(
                _run_pipeline_async(
                    config=config,
                    bundle=bundle,
                    run_id=resolved_run_id,
                    target_languages=target_languages,
                )
            )
        _emit_command_log_sync(
            log_sink,
            _build_command_completed_log(
                timestamp=_now_timestamp(),
                run_id=command_run_id,
                command="run-pipeline",
            ),
        )
        response: ApiResponse[RunExecutionResult] = ApiResponse(
            data=result, error=None, meta=MetaInfo(timestamp=_now_timestamp())
        )
    except Exception as exc:
        error = _error_from_exception(exc)
        if log_sink is not None:
            _emit_command_log_sync(
                log_sink,
                _build_command_failed_log(
                    timestamp=_now_timestamp(),
                    run_id=command_run_id,
                    command="run-pipeline",
                    error=error,
                ),
            )
        response = _error_response(error)
    if progress is not None:
        _render_run_execution_summary(response.data, console=console)
        if response.error is not None:
            _render_run_error(response.error, console=console)
            raise typer.Exit(code=1)
        return
    print(response.model_dump_json())


@app.command("run-phase")
def run_phase(
    config_path: Path = CONFIG_OPTION,
    phase: PhaseName = PHASE_OPTION,
    run_id: str | None = RUN_ID_OPTION,
    target_language: str | None = TARGET_LANGUAGE_SINGLE_OPTION,
    input_path: Path | None = INPUT_PATH_OPTION,
    output_path: Path | None = OUTPUT_PATH_OPTION,
) -> None:
    """Run a single phase (with required prerequisites).

    Raises:
        typer.Exit: When the run fails in interactive mode.
    """
    command_run_id = uuid7()
    log_sink: LogSinkProtocol | None = None
    try:
        config = _load_resolved_config(config_path)
        resolved_run_id = _resolve_run_id(run_id)
        command_run_id = resolved_run_id
        bundle = _build_storage_bundle(
            config, resolved_run_id, allow_console_logs=False
        )
        log_sink = bundle.log_sink
        args: dict[str, JsonValue] = {
            "config_path": str(config_path),
            "run_id": str(resolved_run_id),
            "phase": phase.value,
            "target_language": target_language,
            "input_path": str(input_path) if input_path else None,
            "output_path": str(output_path) if output_path else None,
        }
        _emit_command_log_sync(
            log_sink,
            _build_command_started_log(
                timestamp=_now_timestamp(),
                run_id=command_run_id,
                command="run-phase",
                args=args,
            ),
        )
        if _should_render_progress():
            _render_run_start(
                run_id=resolved_run_id,
                phases=_resolve_phase_plan(config, phase),
                config=config,
                console=None,
            )
        result = asyncio.run(
            _run_phase_async(
                config=config,
                bundle=bundle,
                run_id=resolved_run_id,
                phase=phase,
                target_language=target_language,
                input_path=input_path,
                output_path=output_path,
            )
        )
        _emit_command_log_sync(
            log_sink,
            _build_command_completed_log(
                timestamp=_now_timestamp(),
                run_id=command_run_id,
                command="run-phase",
            ),
        )
        response: ApiResponse[RunExecutionResult] = ApiResponse(
            data=result, error=None, meta=MetaInfo(timestamp=_now_timestamp())
        )
    except Exception as exc:
        error = _error_from_exception(exc)
        if log_sink is not None:
            _emit_command_log_sync(
                log_sink,
                _build_command_failed_log(
                    timestamp=_now_timestamp(),
                    run_id=command_run_id,
                    command="run-phase",
                    error=error,
                ),
            )
        response = _error_response(error)
    if _should_render_progress():
        _render_run_execution_summary(response.data, console=None)
        if response.error is not None:
            _render_run_error(response.error, console=None)
            raise typer.Exit(code=1)
        return
    print(response.model_dump_json())


@app.command("status")
def status(
    config_path: Path = CONFIG_OPTION,
    run_id: str | None = RUN_ID_OPTION,
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch progress"),
    json_output: bool = typer.Option(False, "--json", help="Output status as JSON"),
) -> None:
    """Show run status and progress.

    Raises:
        ValueError: If arguments are incompatible or no runs are found.
        typer.Exit: If rendering fails in non-JSON mode.
    """
    try:
        if watch and json_output:
            raise ValueError("--json is not supported with --watch")
        config = _load_resolved_config(config_path)
        resolved_run_id = _resolve_status_run_id(config, run_id)
        bundle = _build_storage_bundle(config, resolved_run_id)
        if watch:
            _watch_status(bundle, resolved_run_id)
            return
        run_state = asyncio.run(_load_run_state(bundle, resolved_run_id))
        log_reference = asyncio.run(bundle.log_store.get_log_reference(resolved_run_id))
        progress_updates = _read_progress_updates(bundle.progress_path)
        progress_file = _build_progress_reference(bundle.progress_path)
        status_result = build_status_result(
            run_id=resolved_run_id,
            run_state=run_state,
            progress_updates=progress_updates,
            log_reference=log_reference,
            progress_file=progress_file,
        )
        if json_output:
            response: ApiResponse[RunStatusResult] = ApiResponse(
                data=status_result,
                error=None,
                meta=MetaInfo(timestamp=_now_timestamp()),
            )
            print(response.model_dump_json())
            if status_result.status in {RunStatus.FAILED, RunStatus.CANCELLED}:
                raise typer.Exit(code=1)
            return
        _render_status(status_result)
        if status_result.status in {RunStatus.FAILED, RunStatus.CANCELLED}:
            raise typer.Exit(code=1)
    except Exception as exc:
        error = _error_from_exception(exc)
        if json_output:
            response = _error_response(error)
            print(response.model_dump_json())
            return
        rprint(f"[red]Error:[/red] {error.message}")
        raise typer.Exit(code=1) from None


ResponseT = TypeVar("ResponseT")

_LLM_PHASES = {
    PhaseName.CONTEXT,
    PhaseName.PRETRANSLATION,
    PhaseName.TRANSLATE,
    PhaseName.QA,
    PhaseName.EDIT,
}
_LANGUAGE_PHASES = {
    PhaseName.TRANSLATE,
    PhaseName.QA,
    PhaseName.EDIT,
    PhaseName.EXPORT,
}


class _ConfigError(Exception):
    """Raised for CLI configuration issues."""


class _StorageBundle(NamedTuple):
    run_state_store: FileSystemRunStateStore
    artifact_store: FileSystemArtifactStore
    log_store: FileSystemLogStore
    log_sink: LogSinkProtocol
    progress_sink: ProgressSinkProtocol
    progress_path: Path


def _now_timestamp() -> str:
    timestamp = datetime.now(UTC).isoformat()
    return timestamp.replace("+00:00", "Z")


class _ProgressReporter(ProgressSinkProtocol):
    def __init__(
        self,
        sink: ProgressSinkProtocol,
        progress: Progress,
        console: Console,
    ) -> None:
        self._sink = sink
        self._progress = progress
        self._console = console
        self._tasks: dict[str, TaskID] = {}

    async def emit_progress(self, update: ProgressUpdate) -> None:
        await self._sink.emit_progress(update)
        self._handle_update(update)

    def _handle_update(self, update: ProgressUpdate) -> None:
        if update.event == ProgressEvent.PHASE_STARTED and update.phase is not None:
            self._console.print(f"Starting {update.phase}")
        if update.event == ProgressEvent.PHASE_COMPLETED and update.phase is not None:
            self._console.print(f"{update.phase} complete")
        if update.event == ProgressEvent.PHASE_FAILED and update.phase is not None:
            self._console.print(f"{update.phase} failed")

        if update.event != ProgressEvent.PHASE_PROGRESS:
            return

        phase_progress = update.phase_progress
        if phase_progress is None or not phase_progress.metrics:
            return
        metric = phase_progress.metrics[0]
        phase_name = str(update.phase) if update.phase else "phase"
        agent_name = update.message or "agent"
        task_key = f"{phase_name}:{agent_name}"
        description = f"{phase_name}/{agent_name}"
        total = metric.total_units or 0

        task_id = self._tasks.get(task_key)
        if task_id is None:
            task_id = self._progress.add_task(
                description,
                total=total,
                completed=metric.completed_units,
            )
            self._tasks[task_key] = task_id
        else:
            self._progress.update(
                task_id,
                total=total,
                completed=metric.completed_units,
            )
        self._progress.refresh()


def _should_render_progress() -> bool:
    return sys.stderr.isatty()


def _build_progress(console: Console) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
        console=console,
    )


def _as_json_list(values: list[str] | None) -> list[JsonValue] | None:
    if values is None:
        return None
    return list(values)


def _load_resolved_config(config_path: Path) -> RunConfig:
    config = _load_run_config(config_path)
    config = _resolve_project_paths(config, config_path)
    return _resolve_agent_paths(config)


def _resolve_agent_paths(config: RunConfig) -> RunConfig:
    workspace_dir = Path(config.project.paths.workspace_dir)
    agents_config = config.agents
    updated_agents = agents_config.model_copy(
        update={
            "prompts_dir": str(
                _resolve_path(Path(agents_config.prompts_dir), workspace_dir)
            ),
            "agents_dir": str(
                _resolve_path(Path(agents_config.agents_dir), workspace_dir)
            ),
        }
    )
    return config.model_copy(update={"agents": updated_agents})


def _build_command_log_sink(config: RunConfig) -> LogSinkProtocol:
    log_store = FileSystemLogStore(logs_dir=config.project.paths.logs_dir)
    return build_log_sink(config.logging, log_store)


async def _emit_command_log(log_sink: LogSinkProtocol, entry: LogEntry) -> None:
    await log_sink.emit_log(entry)


def _emit_command_log_sync(log_sink: LogSinkProtocol, entry: LogEntry) -> None:
    asyncio.run(_emit_command_log(log_sink, entry))


def _build_command_started_log(
    *,
    timestamp: str,
    run_id: RunId,
    command: str,
    args: dict[str, JsonValue] | None,
) -> LogEntry:
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=CommandEvent.STARTED,
        run_id=run_id,
        phase=None,
        message="Command started",
        data=CommandStartedData(command=command, args=args).model_dump(
            exclude_none=True
        ),
    )


def _build_command_completed_log(
    *,
    timestamp: str,
    run_id: RunId,
    command: str,
) -> LogEntry:
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.INFO,
        event=CommandEvent.COMPLETED,
        run_id=run_id,
        phase=None,
        message="Command completed",
        data=CommandCompletedData(command=command).model_dump(exclude_none=True),
    )


def _build_command_failed_log(
    *,
    timestamp: str,
    run_id: RunId,
    command: str,
    error: ErrorResponse,
) -> LogEntry:
    next_action = _next_action_for_error(error)
    return LogEntry(
        timestamp=timestamp,
        level=LogLevel.ERROR,
        event=CommandEvent.FAILED,
        run_id=run_id,
        phase=None,
        message="Command failed",
        data=CommandFailedData(
            command=command,
            error_code=error.code,
            error_message=error.message,
            next_action=next_action,
        ).model_dump(exclude_none=True),
    )


def _next_action_for_error(error: ErrorResponse) -> str:
    actions = {
        "config_error": "Fix the configuration and retry.",
        "validation_error": "Fix the input or configuration and retry.",
        "missing_dependency": (
            "Provide required inputs or complete dependent phases, then retry."
        ),
        "phase_not_configured": "Enable the phase in the run configuration.",
        "phase_disabled": "Enable the phase or remove it from the run configuration.",
        "phase_execution_failed": "Review phase outputs and logs, then retry.",
        "io_error": "Check file paths or permissions and retry.",
        "runtime_error": "Review the logs and retry.",
    }
    return actions.get(error.code, "Review the logs and retry.")


def _load_translated_lines_sync(path: Path) -> list[TranslatedLine]:
    lines: list[TranslatedLine] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"line {line_number}: JSONL line is not valid JSON"
                    ) from exc
                if not isinstance(payload, dict):
                    raise ValueError(
                        f"line {line_number}: JSONL line must be an object"
                    )
                try:
                    lines.append(TranslatedLine.model_validate(payload))
                except ValidationError as exc:
                    raise ValueError(
                        f"line {line_number}: JSONL line does not match TranslatedLine"
                    ) from exc
    except OSError as exc:
        raise ValueError(f"Failed to read input: {exc}") from exc
    if not lines:
        raise ValueError("No translated lines found in input")
    return lines


async def _load_translated_lines(path: Path) -> list[TranslatedLine]:
    return await asyncio.to_thread(_load_translated_lines_sync, path)


async def _export_async(
    *,
    input_path: Path,
    output_path: Path,
    format: FileFormat,
    untranslated_policy: UntranslatedPolicy,
    include_source_text: bool,
    include_scene_id: bool,
    include_speaker: bool,
    column_order: list[str] | None,
    expected_line_count: int | None,
) -> ExportResult:
    lines = await _load_translated_lines(input_path)
    target = ExportTarget(
        output_path=str(output_path),
        format=format,
        untranslated_policy=untranslated_policy,
        column_order=column_order,
        include_source_text=include_source_text,
        include_scene_id=include_scene_id,
        include_speaker=include_speaker,
        expected_line_count=expected_line_count,
    )
    return await write_output(target, lines)


async def _validate_connection_async(config: RunConfig) -> LlmConnectionReport:
    runtime = _build_llm_runtime()
    targets, unused_endpoints = build_connection_plan(config)
    return await validate_connections(
        runtime,
        targets,
        prompt="Hello world",
        system_prompt="Respond with one short sentence.",
        api_key_lookup=_resolve_api_key,
        skipped_endpoints=unused_endpoints,
    )


def _build_llm_runtime() -> OpenAICompatibleRuntime:
    return OpenAICompatibleRuntime()


def _resolve_api_key(endpoint: LlmEndpointTarget) -> str | None:
    return os.getenv(endpoint.api_key_env)


def _load_run_config(config_path: Path) -> RunConfig:
    _load_dotenv(config_path)
    if not config_path.exists():
        raise _ConfigError(f"Config not found: {config_path}")
    try:
        with open(config_path, "rb") as handle:
            payload: dict[str, JsonValue] = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise _ConfigError(f"Failed to read config: {exc}") from exc
    if not isinstance(payload, dict):
        raise _ConfigError("Config root must be a TOML table")
    return validate_run_config(payload)


def _load_dotenv(config_path: Path) -> None:
    env_path = config_path.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _resolve_project_paths(config: RunConfig, config_path: Path) -> RunConfig:
    config_dir = config_path.parent
    workspace_dir = Path(config.project.paths.workspace_dir)
    if not workspace_dir.is_absolute():
        workspace_dir = (config_dir / workspace_dir).resolve()
    input_path = _resolve_path(Path(config.project.paths.input_path), workspace_dir)
    output_dir = _resolve_path(Path(config.project.paths.output_dir), workspace_dir)
    logs_dir = _resolve_path(Path(config.project.paths.logs_dir), workspace_dir)
    updated_paths = config.project.paths.model_copy(
        update={
            "workspace_dir": str(workspace_dir),
            "input_path": str(input_path),
            "output_dir": str(output_dir),
            "logs_dir": str(logs_dir),
        }
    )
    updated_project = config.project.model_copy(update={"paths": updated_paths})
    return config.model_copy(update={"project": updated_project})


def _resolve_path(path: Path, base_dir: Path) -> Path:
    base_dir = base_dir.resolve()
    resolved = path if path.is_absolute() else base_dir / path
    resolved = resolved.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise _ConfigError(f"Path must stay within workspace: {resolved}") from exc
    return resolved


def _resolve_run_id(run_id: str | None) -> RunId:
    if run_id is None:
        return uuid7()
    return _parse_run_id(run_id)


def _parse_run_id(run_id: str) -> RunId:
    try:
        value = UUID(run_id)
    except ValueError as exc:
        raise ValueError("run_id must be a valid UUIDv7") from exc
    if value.version != 7:
        raise ValueError("run_id must be a valid UUIDv7")
    return value


def _resolve_target_languages(
    config: RunConfig, target_languages: list[str] | None
) -> list[LanguageCode]:
    if target_languages is None:
        return config.project.languages.target_languages
    validated = LanguageConfig(
        source_language=config.project.languages.source_language,
        target_languages=target_languages,
    )
    return validated.target_languages


def _resolve_phase_languages(
    config: RunConfig, phase: PhaseName, target_language: str | None
) -> list[LanguageCode]:
    if phase not in _LANGUAGE_PHASES:
        if target_language is not None:
            raise ValueError("target_language is only valid for language phases")
        return []
    if target_language is not None:
        return _resolve_target_languages(config, [target_language])
    if len(config.project.languages.target_languages) == 1:
        return config.project.languages.target_languages
    raise ValueError("target_language is required when multiple targets are configured")


def _resolve_phase_model(config: RunConfig, phase: PhaseName) -> ModelSettings | None:
    for entry in config.pipeline.phases:
        if entry.phase == phase:
            if entry.model is not None:
                return entry.model
            return config.pipeline.default_model
    return config.pipeline.default_model


def _resolve_enabled_phases(config: RunConfig) -> list[PhaseName]:
    return [PhaseName(phase.phase) for phase in config.pipeline.phases if phase.enabled]


def _resolve_phase_plan(config: RunConfig, phase: PhaseName) -> list[PhaseName]:
    ordered = [PhaseName(entry.phase) for entry in config.pipeline.phases]
    if phase not in ordered:
        raise ValueError(f"Phase {phase.value} is not configured")
    phase_config = next(
        entry for entry in config.pipeline.phases if entry.phase == phase
    )
    if not phase_config.enabled:
        raise ValueError(f"Phase {phase.value} is disabled")
    index = ordered.index(phase)
    return [
        PhaseName(entry.phase)
        for entry in config.pipeline.phases[: index + 1]
        if entry.enabled
    ]


def _ensure_api_key(config: RunConfig, phases: list[PhaseName]) -> None:
    if not any(phase in _LLM_PHASES for phase in phases):
        return
    if config.endpoints is None:
        endpoint = config.endpoint
        if endpoint is None:
            raise _ConfigError("Missing endpoint configuration")
        env_var = endpoint.api_key_env
        if os.getenv(env_var) is None:
            raise _ConfigError(f"Missing API key environment variable: {env_var}")
        return
    lookup = {
        endpoint.provider_name: endpoint for endpoint in config.endpoints.endpoints
    }
    used_refs: set[str] = set()
    for phase in phases:
        if phase not in _LLM_PHASES:
            continue
        model = _resolve_phase_model(config, phase)
        endpoint_ref = config.resolve_endpoint_ref(model=model)
        if endpoint_ref is None:
            continue
        used_refs.add(endpoint_ref)
    for endpoint_ref in sorted(used_refs):
        endpoint = lookup.get(endpoint_ref)
        if endpoint is None:
            raise _ConfigError(f"Unknown endpoint reference: {endpoint_ref}")
        env_var = endpoint.api_key_env
        if os.getenv(env_var) is None:
            raise _ConfigError(
                "Missing API key environment variable: "
                f"{env_var} (endpoint: {endpoint_ref})"
            )


def _build_storage_bundle(
    config: RunConfig,
    run_id: RunId,
    progress_sink: ProgressSinkProtocol | None = None,
    *,
    allow_console_logs: bool = True,
) -> _StorageBundle:
    workspace_dir = Path(config.project.paths.workspace_dir)
    base_dir = workspace_dir / ".rentl"
    run_state_dir = base_dir / "run_state"
    artifact_dir = base_dir / "artifacts"
    log_store = FileSystemLogStore(logs_dir=config.project.paths.logs_dir)
    progress_path = _progress_path(config.project.paths.logs_dir, run_id)
    logging_config = _build_logging_config(config, allow_console_logs)
    log_sink = build_log_sink(logging_config, log_store)
    file_progress_sink = FileSystemProgressSink(str(progress_path))
    return _StorageBundle(
        run_state_store=FileSystemRunStateStore(base_dir=str(run_state_dir)),
        artifact_store=FileSystemArtifactStore(base_dir=str(artifact_dir)),
        log_store=log_store,
        log_sink=log_sink,
        progress_sink=progress_sink or file_progress_sink,
        progress_path=progress_path,
    )


def _build_logging_config(config: RunConfig, allow_console_logs: bool) -> LoggingConfig:
    if allow_console_logs:
        return config.logging
    sinks = [sink for sink in config.logging.sinks if sink.type != LogSinkType.CONSOLE]
    if not sinks:
        sinks = [LogSinkConfig(type=LogSinkType.FILE)]
    return LoggingConfig(sinks=sinks)


def _render_run_start(
    *,
    run_id: RunId,
    phases: list[PhaseName],
    config: RunConfig,
    console: Console | None,
) -> None:
    phase_list = ", ".join(str(phase) for phase in phases) or "n/a"
    agent_lines: list[str] = []
    phase_set = {str(phase) for phase in phases}
    for entry in config.pipeline.phases:
        phase_value = str(entry.phase)
        if phase_value not in phase_set:
            continue
        if not entry.agents:
            continue
        agents = ", ".join(entry.agents)
        agent_lines.append(f"{phase_value}: {agents}")
    agent_text = "\n".join(agent_lines) or "n/a"
    started = _now_timestamp()
    message = (
        f"Run {run_id} starting\n"
        f"Started: {started}\n"
        f"Phases: {phase_list}\n"
        f"Agents:\n{agent_text}"
    )
    if console is not None:
        console.print(message)
    else:
        rprint(message)


def _render_run_execution_summary(
    result: RunExecutionResult | None,
    *,
    console: Console | None,
) -> None:
    if result is None:
        return
    status = _format_enum(result.status)
    started_at = result.run_state.metadata.started_at if result.run_state else None
    completed_at = result.run_state.metadata.completed_at if result.run_state else None
    log_path = (
        result.log_file.location.path
        if result.log_file and result.log_file.location.path
        else "n/a"
    )
    progress_path = result.progress_file.path if result.progress_file else "n/a"

    table = Table.grid(padding=(0, 1))
    table.add_column(justify="right", style="bold")
    table.add_column()
    table.add_row("Run ID", str(result.run_id))
    table.add_row("Status", status)
    if started_at:
        table.add_row("Started", started_at)
    if completed_at:
        table.add_row("Completed", completed_at)
    table.add_row("Log file", log_path)
    table.add_row("Progress file", progress_path)

    panel = Panel(table, title="rentl run", expand=False)
    if console is not None:
        console.print(panel)
    else:
        rprint(panel)


def _render_run_error(error: ErrorResponse, *, console: Console | None) -> None:
    message = f"[red]Error:[/red] {error.message}"
    if console is not None:
        console.print(message)
    else:
        rprint(message)


def _progress_path(logs_dir: str, run_id: RunId) -> Path:
    return Path(logs_dir) / "progress" / f"{run_id}.jsonl"


def _build_orchestrator(
    config: RunConfig, bundle: _StorageBundle, phases: list[PhaseName]
) -> PipelineOrchestrator:
    agent_pools = None
    if any(phase in _LLM_PHASES for phase in phases):
        telemetry_emitter = AgentTelemetryEmitter(
            progress_sink=bundle.progress_sink,
            log_sink=bundle.log_sink,
            clock=_now_timestamp,
        )
        try:
            agent_pools = build_agent_pools(
                config=config,
                telemetry_emitter=telemetry_emitter,
                phases=phases,
            )
        except ValueError as exc:
            raise _ConfigError(str(exc)) from exc
    return PipelineOrchestrator(
        ingest_adapter=get_ingest_adapter(config.project.formats.input_format),
        export_adapter=get_export_adapter(config.project.formats.output_format),
        context_agents=agent_pools.context_agents if agent_pools else None,
        pretranslation_agents=agent_pools.pretranslation_agents
        if agent_pools
        else None,
        translate_agents=agent_pools.translate_agents if agent_pools else None,
        qa_agents=agent_pools.qa_agents if agent_pools else None,
        edit_agents=agent_pools.edit_agents if agent_pools else None,
        log_sink=bundle.log_sink,
        progress_sink=bundle.progress_sink,
        run_state_store=bundle.run_state_store,
        artifact_store=bundle.artifact_store,
    )


async def _load_or_create_run_context(
    orchestrator: PipelineOrchestrator,
    bundle: _StorageBundle,
    run_id: RunId,
    config: RunConfig,
) -> PipelineRunContext:
    record = await bundle.run_state_store.load_run_state(run_id)
    if record is None:
        return orchestrator.create_run(run_id=run_id, config=config)
    return hydrate_run_context(config, record.state)


def _build_ingest_source(
    config: RunConfig,
    phases: list[PhaseName],
    input_path: Path | None,
) -> IngestSource | None:
    if PhaseName.INGEST not in phases:
        if input_path is not None:
            raise ValueError("input_path is only valid when running ingest")
        return None
    workspace_dir = Path(config.project.paths.workspace_dir)
    resolved = input_path or Path(config.project.paths.input_path)
    if input_path is not None:
        resolved = _resolve_path(resolved, workspace_dir)
    return IngestSource(
        input_path=str(resolved),
        format=FileFormat(config.project.formats.input_format),
    )


def _build_export_targets(
    config: RunConfig,
    phases: list[PhaseName],
    run_id: RunId,
    target_languages: list[LanguageCode] | None,
    output_path: Path | None,
) -> dict[LanguageCode, ExportTarget] | None:
    if PhaseName.EXPORT not in phases:
        if output_path is not None:
            raise ValueError("output_path is only valid when running export")
        return None
    languages = target_languages or config.project.languages.target_languages
    if not languages:
        raise ValueError("No target languages configured")
    if output_path is not None and len(languages) > 1:
        raise ValueError("output_path requires a single target language")
    output_format = FileFormat(config.project.formats.output_format)
    output_dir = Path(config.project.paths.output_dir)
    run_dir = output_dir / f"run-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    resolved_override: Path | None = None
    if output_path is not None:
        resolved_override = _resolve_path(
            output_path, Path(config.project.paths.workspace_dir)
        )
    targets: dict[LanguageCode, ExportTarget] = {}
    for language in languages:
        path = resolved_override
        if path is None:
            path = run_dir / f"{language}.{output_format.value}"
        target = ExportTarget(output_path=str(path), format=output_format)
        targets[language] = target
    return targets


async def _load_run_state(bundle: _StorageBundle, run_id: RunId) -> RunState | None:
    record = await bundle.run_state_store.load_run_state(run_id)
    if record is None:
        return None
    return record.state


async def _run_pipeline_async(
    *,
    config: RunConfig,
    bundle: _StorageBundle,
    run_id: RunId,
    target_languages: list[str] | None,
) -> RunExecutionResult:
    phases = _resolve_enabled_phases(config)
    if not phases:
        raise ValueError("No enabled phases configured")
    languages = _resolve_target_languages(config, target_languages)
    _ensure_api_key(config, phases)
    orchestrator = _build_orchestrator(config, bundle, phases)
    run = await _load_or_create_run_context(orchestrator, bundle, run_id, config)
    ingest_source = _build_ingest_source(config, phases, input_path=None)
    export_targets = _build_export_targets(
        config, phases, run.run_id, languages, output_path=None
    )
    await orchestrator.run_plan(
        run,
        phases=phases,
        target_languages=languages,
        ingest_source=ingest_source,
        export_targets=export_targets,
    )
    run_state = await _load_run_state(bundle, run.run_id)
    log_reference = await bundle.log_store.get_log_reference(run.run_id)
    progress_file = _build_progress_reference(bundle.progress_path)
    return _build_run_execution_result(
        run=run,
        run_state=run_state,
        log_reference=log_reference,
        progress_file=progress_file,
        phase_record=None,
    )


async def _run_phase_async(
    *,
    config: RunConfig,
    bundle: _StorageBundle,
    run_id: RunId,
    phase: PhaseName,
    target_language: str | None,
    input_path: Path | None,
    output_path: Path | None,
) -> RunExecutionResult:
    phases = _resolve_phase_plan(config, phase)
    languages = _resolve_phase_languages(config, phase, target_language)
    _ensure_api_key(config, phases)
    orchestrator = _build_orchestrator(config, bundle, phases)
    run = await _load_or_create_run_context(orchestrator, bundle, run_id, config)
    ingest_source = _build_ingest_source(config, phases, input_path=input_path)
    export_targets = _build_export_targets(
        config,
        phases,
        run.run_id,
        languages or None,
        output_path=output_path,
    )
    await orchestrator.run_plan(
        run,
        phases=phases,
        target_languages=languages or None,
        ingest_source=ingest_source,
        export_targets=export_targets,
    )
    run_state = await _load_run_state(bundle, run.run_id)
    log_reference = await bundle.log_store.get_log_reference(run.run_id)
    progress_file = _build_progress_reference(bundle.progress_path)
    phase_record = _find_phase_record(run.phase_history, phase, languages)
    return _build_run_execution_result(
        run=run,
        run_state=run_state,
        log_reference=log_reference,
        progress_file=progress_file,
        phase_record=phase_record,
    )


def _find_phase_record(
    history: list[PhaseRunRecord],
    phase: PhaseName,
    languages: list[LanguageCode] | None,
) -> PhaseRunRecord | None:
    target_language: LanguageCode | None = None
    if languages:
        target_language = languages[0]
    matches = [
        record
        for record in history
        if record.phase == phase and record.target_language == target_language
    ]
    if not matches:
        return None
    return matches[-1]


def _build_progress_reference(path: Path | None) -> StorageReference | None:
    if path is None:
        return None
    return StorageReference(backend=StorageBackend.FILESYSTEM, path=str(path))


def _resolve_status_run_id(config: RunConfig, run_id: str | None) -> RunId:
    if run_id is not None:
        return _parse_run_id(run_id)
    workspace_dir = Path(config.project.paths.workspace_dir)
    run_state_dir = workspace_dir / ".rentl" / "run_state"
    store = FileSystemRunStateStore(base_dir=str(run_state_dir))
    records = asyncio.run(store.list_run_index(limit=1))
    if not records:
        raise ValueError("No runs found")
    return records[0].metadata.run_id


def _read_progress_updates(path: Path) -> list[ProgressUpdate]:
    if not path.exists():
        return []
    updates: list[ProgressUpdate] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            updates.append(ProgressUpdate.model_validate_json(line))
    return updates


def _read_progress_updates_since(
    path: Path, offset: int
) -> tuple[list[ProgressUpdate], int]:
    if not path.exists():
        return [], offset
    updates: list[ProgressUpdate] = []
    with path.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        for line in handle:
            if not line.strip():
                continue
            updates.append(ProgressUpdate.model_validate_json(line))
        new_offset = handle.tell()
    return updates, new_offset


def _watch_status(bundle: _StorageBundle, run_id: RunId) -> None:
    updates: list[ProgressUpdate] = []
    offset = 0
    log_reference = asyncio.run(bundle.log_store.get_log_reference(run_id))
    progress_file = _build_progress_reference(bundle.progress_path)
    final_status = None
    no_state_count = 0
    max_no_state_iterations = 20  # 10 seconds of no state before warning

    with Live(refresh_per_second=4) as live:
        while True:
            run_state = asyncio.run(_load_run_state(bundle, run_id))
            new_updates, offset = _read_progress_updates_since(
                bundle.progress_path, offset
            )
            if new_updates:
                updates.extend(new_updates)
            status_result = build_status_result(
                run_id=run_id,
                run_state=run_state,
                progress_updates=updates,
                log_reference=log_reference,
                progress_file=progress_file,
            )
            live.update(_build_status_panel(status_result))

            # Determine terminal status from status snapshot
            terminal_status = status_result.status
            if run_state is not None:
                no_state_count = 0
            else:
                no_state_count += 1

            # Check for terminal states
            if _format_enum(terminal_status) in {
                RunStatus.COMPLETED.value,
                RunStatus.FAILED.value,
                RunStatus.CANCELLED.value,
            }:
                final_status = terminal_status
                break

            # If no state for too long, show warning in the panel
            if no_state_count > max_no_state_iterations:
                # Force update with warning that no state exists
                warning_result = _build_no_state_warning_result(
                    run_id, status_result, no_state_count
                )
                live.update(_build_status_panel(warning_result))
                final_status = RunStatus.FAILED
                break

            time.sleep(0.5)

    if final_status is None:
        final_status = status_result.status
    rprint(f"Run {run_id} {final_status.value}")
    if _format_enum(final_status) in {
        RunStatus.FAILED.value,
        RunStatus.CANCELLED.value,
    }:
        raise typer.Exit(code=1)


def _render_status(result: RunStatusResult) -> None:
    panel = _build_status_panel(result)
    rprint(panel)


def _build_status_panel(result: RunStatusResult) -> Panel:
    header = Table.grid(padding=(0, 1))
    header.add_column(justify="right", style="bold")
    header.add_column()
    header.add_row("Run ID", str(result.run_id))
    header.add_row("Status", _format_enum(result.status))
    header.add_row(
        "Current Phase",
        _format_enum(result.current_phase) if result.current_phase else "n/a",
    )
    header.add_row("Updated", result.updated_at)
    if result.progress is not None:
        header.add_row(
            "Run Progress",
            _format_percent(result.progress.summary.percent_complete),
        )
        header.add_row(
            "Run ETA",
            _format_eta(result.progress.summary.eta_seconds),
        )

    phases_table = _build_phase_table(result.progress)
    agent_table = _build_agent_summary_table(result)
    active_agents = _build_active_agent_table(result)
    phase_summary = _build_phase_summary_table(result.run_state)
    error_table = _build_error_table(result.run_state)

    renderables: list[RenderableType] = [header, phases_table]
    if agent_table is not None:
        renderables.append(agent_table)
    if active_agents is not None:
        renderables.append(active_agents)
    if phase_summary is not None:
        renderables.append(phase_summary)
    if error_table is not None:
        renderables.append(error_table)

    return Panel(Group(*renderables), title="rentl status", expand=True)


def _build_phase_table(progress: RunProgress | None) -> Table:
    table = Table(title="Phases", show_lines=False)
    table.add_column("Phase")
    table.add_column("Status")
    table.add_column("Progress")
    table.add_column("ETA")
    if progress is None:
        table.add_row("n/a", "n/a", "n/a", "n/a")
        return table
    for phase in progress.phases:
        table.add_row(
            _format_enum(phase.phase),
            _format_enum(phase.status),
            _format_phase_progress(phase),
            _format_eta(phase.summary.eta_seconds),
        )
    return table


def _build_agent_summary_table(result: RunStatusResult) -> Table | None:
    if result.agent_summary is None:
        return None
    table = Table(title="Agents")
    table.add_column("Status")
    table.add_column("Count", justify="right")
    by_status = {
        str(key): value for key, value in result.agent_summary.by_status.items()
    }
    for status in AgentStatus:
        count = by_status.get(status.value, 0)
        if count:
            table.add_row(status.value, str(count))
    table.add_row("total", str(result.agent_summary.total))
    if result.agent_summary.usage is not None:
        table.add_row(
            "tokens",
            str(result.agent_summary.usage.total_tokens),
        )
        table.add_row(
            "requests",
            str(result.agent_summary.usage.request_count),
        )
    return table


def _build_active_agent_table(result: RunStatusResult) -> Table | None:
    if not result.agents:
        return None
    running = [agent for agent in result.agents if agent.status == AgentStatus.RUNNING]
    if not running:
        return None
    table = Table(title="Active Agents")
    table.add_column("Agent")
    table.add_column("Phase")
    table.add_column("Target")
    table.add_column("Attempt", justify="right")
    table.add_column("Started")
    for agent in running[:5]:
        table.add_row(
            agent.agent_name,
            _format_enum(agent.phase),
            agent.target_language or "-",
            str(agent.attempt or "-"),
            agent.started_at or "-",
        )
    if len(running) > 5:
        table.add_row(
            f"+{len(running) - 5} more",
            "",
            "",
            "",
            "",
        )
    return table


def _build_phase_summary_table(run_state: RunState | None) -> Table | None:
    if run_state is None or not run_state.phase_history:
        return None
    latest: dict[tuple[PhaseName, str | None], PhaseRunRecord] = {}
    for record in run_state.phase_history:
        if record.summary is None:
            continue
        key = (record.phase, record.target_language)
        latest[key] = record
    if not latest:
        return None
    table = Table(title="Phase Summaries")
    table.add_column("Phase")
    table.add_column("Target")
    table.add_column("Metrics")
    order = {phase.value: index for index, phase in enumerate(PIPELINE_PHASE_ORDER)}
    for key in sorted(
        latest.keys(),
        key=lambda item: order.get(_format_enum(item[0]), 0),
    ):
        record = latest[key]
        summary = record.summary
        if summary is None:
            continue
        metrics = _format_result_metrics(summary.metrics)
        table.add_row(
            _format_enum(record.phase),
            record.target_language or "-",
            metrics,
        )
    return table


def _build_error_table(run_state: RunState | None) -> Table | None:
    if run_state is None or run_state.last_error is None:
        return None
    error = run_state.last_error
    details = error.details or {}
    table = Table(title="Run Error")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("code", error.code)
    table.add_row("message", error.message)
    phase = details.get("phase")
    if phase:
        table.add_row("phase", str(phase))
    target_language = details.get("target_language")
    if target_language:
        table.add_row("target_language", str(target_language))
    missing = details.get("missing_phases")
    if missing:
        if isinstance(missing, list):
            table.add_row(
                "missing_phases",
                ", ".join(str(item) for item in missing),
            )
        else:
            table.add_row("missing_phases", str(missing))
    next_action = details.get("next_action")
    if next_action:
        table.add_row("next_action", str(next_action))
    return table


def _format_phase_progress(phase: PhaseProgress) -> str:
    percent = phase.summary.percent_complete
    metric = _format_progress_metric(phase.metrics)
    if percent is None:
        return metric or "n/a"
    if metric:
        return f"{percent:.1f}% ({metric})"
    return f"{percent:.1f}%"


def _format_progress_metric(metrics: list[ProgressMetric] | None) -> str | None:
    if not metrics:
        return None
    metric = metrics[0]
    unit_value = _format_enum(metric.unit)
    if metric.total_units is None:
        return f"{metric.completed_units} {unit_value}"
    return f"{metric.completed_units}/{metric.total_units} {unit_value}"


def _build_no_state_warning_result(
    run_id: RunId,
    base_result: RunStatusResult,
    iterations: int,
) -> RunStatusResult:
    """Build a status result with warning when no run state exists.

    Args:
        run_id: The run identifier being watched.
        base_result: The original status result.
        iterations: Number of iterations without state.

    Returns:
        RunStatusResult with warning information.
    """
    # If we have a run_state, update its error; otherwise the error table won't show
    # Instead, we'll add this to the phase summary or create a synthetic status
    if base_result.run_state is None:
        # Return result with failed status to surface the issue
        return replace(
            base_result,
            status=RunStatus.FAILED,
            run_state=None,
        )
    return base_result


def _format_result_metrics(metrics: list[PhaseResultMetric]) -> str:
    parts: list[str] = []
    for metric in metrics:
        value = metric.value
        if metric.unit == ResultMetricUnit.RATIO:
            formatted = f"{float(value) * 100:.1f}%"
            parts.append(f"{metric.metric_key}: {formatted}")
            continue
        else:
            formatted = f"{int(value)}"
        parts.append(f"{metric.metric_key}: {formatted} {_format_enum(metric.unit)}")
    return ", ".join(parts)


def _format_eta(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    remaining = int(seconds)
    if remaining <= 0:
        return "0s"
    minutes, seconds = divmod(remaining, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _format_percent(percent: float | None) -> str:
    if percent is None:
        return "n/a"
    return f"{percent:.1f}%"


def _format_enum(value: Enum | str | int | float | bool | None) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _build_run_execution_result(
    *,
    run: PipelineRunContext,
    run_state: RunState | None,
    log_reference: LogFileReference | None,
    progress_file: StorageReference | None,
    phase_record: PhaseRunRecord | None,
) -> RunExecutionResult:
    progress: ProgressSummary | None = None
    if run_state is not None:
        progress = run_state.progress.summary
    else:
        progress = run.progress.summary
    return RunExecutionResult(
        run_id=run.run_id,
        status=run.status,
        progress=progress,
        run_state=run_state,
        log_file=log_reference,
        progress_file=progress_file,
        phase_record=phase_record,
    )


def _error_response(error: ErrorResponse) -> ApiResponse[ResponseT]:
    return ApiResponse(
        data=None,
        error=error,
        meta=MetaInfo(timestamp=_now_timestamp()),
    )


def _summarize_batch_error(
    error: ErrorResponse, count: int, label: str
) -> ErrorResponse:
    if count <= 1:
        return error
    return ErrorResponse(
        code=error.code,
        message=f"{count} {label} errors; first: {error.message}",
        details=error.details,
    )


def _error_from_exception(exc: Exception) -> ErrorResponse:
    if isinstance(exc, OrchestrationError):
        return exc.info.to_error_response()
    if isinstance(exc, IngestBatchError):
        error = exc.errors[0].to_error_response()
        return _summarize_batch_error(error, len(exc.errors), "ingest")
    if isinstance(exc, IngestError):
        return exc.info.to_error_response()
    if isinstance(exc, ExportBatchError):
        error = exc.errors[0].to_error_response()
        return _summarize_batch_error(error, len(exc.errors), "export")
    if isinstance(exc, ExportError):
        return exc.info.to_error_response()
    if isinstance(exc, StorageBatchError):
        error = exc.errors[0].to_error_response()
        return _summarize_batch_error(error, len(exc.errors), "storage")
    if isinstance(exc, StorageError):
        return exc.info.to_error_response()
    if isinstance(exc, ValidationError):
        message = "Config validation failed"
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = first.get("loc", [])
            label = ".".join(str(part) for part in loc) if loc else ""
            detail = first.get("msg", "")
            if label and detail:
                message = f"Config validation failed: {label} - {detail}"
            elif detail:
                message = f"Config validation failed: {detail}"
        return ErrorResponse(code="validation_error", message=message, details=None)
    if isinstance(exc, _ConfigError):
        return ErrorResponse(code="config_error", message=str(exc), details=None)
    if isinstance(exc, ValueError):
        return ErrorResponse(code="validation_error", message=str(exc), details=None)
    return ErrorResponse(code="runtime_error", message=str(exc), details=None)


def _batch_error_response(exc: ExportBatchError) -> ApiResponse[ExportResult]:
    error = _summarize_batch_error(
        exc.errors[0].to_error_response(), len(exc.errors), "export"
    )
    return _error_response(error)


if __name__ == "__main__":
    app()
