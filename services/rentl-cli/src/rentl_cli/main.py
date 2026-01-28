"""CLI entry point - thin adapter over rentl-core."""

from __future__ import annotations

import asyncio
import json
import os
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple, TypeVar
from uuid import UUID, uuid7

import typer
from dotenv import load_dotenv
from pydantic import ValidationError
from rich import print as rprint

from rentl_core import VERSION
from rentl_core.llm.connection import build_connection_plan, validate_connections
from rentl_core.orchestrator import (
    PipelineOrchestrator,
    PipelineRunContext,
    hydrate_run_context,
)
from rentl_core.ports.export import ExportBatchError, ExportError, ExportResult
from rentl_core.ports.ingest import IngestBatchError, IngestError
from rentl_core.ports.orchestrator import OrchestrationError
from rentl_core.ports.storage import StorageBatchError, StorageError
from rentl_io import write_output
from rentl_io.export.router import get_export_adapter
from rentl_io.ingest.router import get_ingest_adapter
from rentl_io.storage.filesystem import (
    FileSystemArtifactStore,
    FileSystemLogStore,
    FileSystemRunStateStore,
)
from rentl_io.storage.log_sink import StorageLogSink
from rentl_io.storage.progress_sink import FileSystemProgressSink
from rentl_llm import OpenAICompatibleRuntime
from rentl_schemas.config import LanguageConfig, ModelSettings, RunConfig
from rentl_schemas.io import ExportTarget, IngestSource, TranslatedLine
from rentl_schemas.llm import LlmConnectionReport, LlmEndpointTarget
from rentl_schemas.pipeline import PhaseRunRecord, RunState
from rentl_schemas.primitives import (
    FileFormat,
    LanguageCode,
    PhaseName,
    RunId,
    UntranslatedPolicy,
)
from rentl_schemas.progress import ProgressSummary
from rentl_schemas.responses import (
    ApiResponse,
    ErrorResponse,
    MetaInfo,
    RunExecutionResult,
)
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
    try:
        result = asyncio.run(
            _validate_connection_async(
                config_path=config_path,
            )
        )
        response: ApiResponse[LlmConnectionReport] = ApiResponse(
            data=result,
            error=None,
            meta=MetaInfo(timestamp=_now_timestamp()),
        )
    except Exception as exc:
        response = _error_response(_error_from_exception(exc))
    print(response.model_dump_json())


@app.command()
def export(
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
    try:
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
        response: ApiResponse[ExportResult] = ApiResponse(
            data=result, error=None, meta=MetaInfo(timestamp=_now_timestamp())
        )
    except ExportBatchError as exc:
        response = _batch_error_response(exc)
    except ExportError as exc:
        response = _error_response(exc.info.to_error_response())
    except ValueError as exc:
        response = _error_response(
            ErrorResponse(code="validation_error", message=str(exc), details=None)
        )

    print(response.model_dump_json())


@app.command("run-pipeline")
def run_pipeline(
    config_path: Path = CONFIG_OPTION,
    run_id: str | None = RUN_ID_OPTION,
    target_languages: list[str] | None = TARGET_LANGUAGE_OPTION,
) -> None:
    """Run the full pipeline plan."""
    try:
        result = asyncio.run(
            _run_pipeline_async(
                config_path=config_path,
                run_id=run_id,
                target_languages=target_languages,
            )
        )
        response: ApiResponse[RunExecutionResult] = ApiResponse(
            data=result, error=None, meta=MetaInfo(timestamp=_now_timestamp())
        )
    except Exception as exc:
        response = _error_response(_error_from_exception(exc))
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
    """Run a single phase (with required prerequisites)."""
    try:
        result = asyncio.run(
            _run_phase_async(
                config_path=config_path,
                phase=phase,
                run_id=run_id,
                target_language=target_language,
                input_path=input_path,
                output_path=output_path,
            )
        )
        response: ApiResponse[RunExecutionResult] = ApiResponse(
            data=result, error=None, meta=MetaInfo(timestamp=_now_timestamp())
        )
    except Exception as exc:
        response = _error_response(_error_from_exception(exc))
    print(response.model_dump_json())


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
    log_sink: StorageLogSink
    progress_sink: FileSystemProgressSink
    progress_path: Path


def _now_timestamp() -> str:
    timestamp = datetime.now(UTC).isoformat()
    return timestamp.replace("+00:00", "Z")


def _load_translated_lines_sync(path: Path) -> list[TranslatedLine]:
    lines: list[TranslatedLine] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if raw_line.strip() == "":
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


async def _validate_connection_async(config_path: Path) -> LlmConnectionReport:
    config = _resolve_project_paths(_load_run_config(config_path), config_path)
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
            payload = tomllib.load(handle)
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


def _build_storage_bundle(config: RunConfig, run_id: RunId) -> _StorageBundle:
    workspace_dir = Path(config.project.paths.workspace_dir)
    base_dir = workspace_dir / ".rentl"
    run_state_dir = base_dir / "run_state"
    artifact_dir = base_dir / "artifacts"
    log_store = FileSystemLogStore(logs_dir=config.project.paths.logs_dir)
    progress_path = _progress_path(config.project.paths.logs_dir, run_id)
    return _StorageBundle(
        run_state_store=FileSystemRunStateStore(base_dir=str(run_state_dir)),
        artifact_store=FileSystemArtifactStore(base_dir=str(artifact_dir)),
        log_store=log_store,
        log_sink=StorageLogSink(log_store),
        progress_sink=FileSystemProgressSink(str(progress_path)),
        progress_path=progress_path,
    )


def _progress_path(logs_dir: str, run_id: RunId) -> Path:
    return Path(logs_dir) / "progress" / f"{run_id}.jsonl"


def _build_orchestrator(
    config: RunConfig, bundle: _StorageBundle
) -> PipelineOrchestrator:
    return PipelineOrchestrator(
        ingest_adapter=get_ingest_adapter(config.project.formats.input_format),
        export_adapter=get_export_adapter(config.project.formats.output_format),
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
    config_path: Path,
    run_id: str | None,
    target_languages: list[str] | None,
) -> RunExecutionResult:
    config = _resolve_project_paths(_load_run_config(config_path), config_path)
    phases = _resolve_enabled_phases(config)
    if not phases:
        raise ValueError("No enabled phases configured")
    languages = _resolve_target_languages(config, target_languages)
    _ensure_api_key(config, phases)
    resolved_run_id = _resolve_run_id(run_id)
    bundle = _build_storage_bundle(config, resolved_run_id)
    orchestrator = _build_orchestrator(config, bundle)
    run = await _load_or_create_run_context(
        orchestrator, bundle, resolved_run_id, config
    )
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
    config_path: Path,
    phase: PhaseName,
    run_id: str | None,
    target_language: str | None,
    input_path: Path | None,
    output_path: Path | None,
) -> RunExecutionResult:
    config = _resolve_project_paths(_load_run_config(config_path), config_path)
    phases = _resolve_phase_plan(config, phase)
    languages = _resolve_phase_languages(config, phase, target_language)
    _ensure_api_key(config, phases)
    resolved_run_id = _resolve_run_id(run_id)
    bundle = _build_storage_bundle(config, resolved_run_id)
    orchestrator = _build_orchestrator(config, bundle)
    run = await _load_or_create_run_context(
        orchestrator, bundle, resolved_run_id, config
    )
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
