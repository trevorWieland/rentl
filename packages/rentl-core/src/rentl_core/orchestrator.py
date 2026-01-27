"""Core pipeline orchestration logic."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TypeVar, cast
from uuid import uuid7

from rentl_core.ports.export import ExportAdapterProtocol, ExportResult
from rentl_core.ports.ingest import IngestAdapterProtocol
from rentl_core.ports.orchestrator import (
    ContextAgentPoolProtocol,
    EditAgentPoolProtocol,
    LogSinkProtocol,
    OrchestrationError,
    OrchestrationErrorCode,
    OrchestrationErrorDetails,
    OrchestrationErrorInfo,
    PhaseAgentPoolProtocol,
    PhaseAgentProtocol,
    PretranslationAgentPoolProtocol,
    ProgressSinkProtocol,
    QaAgentPoolProtocol,
    TranslateAgentPoolProtocol,
    build_artifact_persist_failed_log,
    build_artifact_persisted_log,
    build_phase_log,
    build_run_completed_log,
    build_run_failed_log,
    build_run_started_log,
)
from rentl_core.ports.storage import ArtifactStoreProtocol, RunStateStoreProtocol
from rentl_schemas.base import BaseSchema
from rentl_schemas.config import PhaseConfig, PhaseExecutionConfig, RunConfig
from rentl_schemas.events import PhaseEventSuffix, ProgressEvent
from rentl_schemas.io import ExportTarget, IngestSource, SourceLine, TranslatedLine
from rentl_schemas.logs import LogEntry
from rentl_schemas.phases import (
    ContextNote,
    ContextPhaseInput,
    ContextPhaseOutput,
    EditPhaseInput,
    EditPhaseOutput,
    GlossaryTerm,
    PretranslationAnnotation,
    PretranslationPhaseInput,
    PretranslationPhaseOutput,
    QaPhaseInput,
    QaPhaseOutput,
    SceneSummary,
    TermCandidate,
    TranslatePhaseInput,
    TranslatePhaseOutput,
)
from rentl_schemas.pipeline import (
    ArtifactReference,
    PhaseArtifacts,
    PhaseDependency,
    PhaseRevision,
    PhaseRunRecord,
    RunError,
    RunMetadata,
    RunState,
)
from rentl_schemas.primitives import (
    AnnotationId,
    ArtifactId,
    FileFormat,
    IssueId,
    JsonValue,
    LanguageCode,
    LineId,
    NoteId,
    PhaseName,
    PhaseStatus,
    PhaseWorkStrategy,
    QaCategory,
    QaSeverity,
    RouteId,
    RunId,
    RunStatus,
    Timestamp,
)
from rentl_schemas.progress import (
    PhaseProgress,
    ProgressMetric,
    ProgressPercentMode,
    ProgressSummary,
    ProgressTotalStatus,
    ProgressUnit,
    ProgressUpdate,
    RunProgress,
    compute_phase_summary,
    compute_run_summary,
)
from rentl_schemas.qa import LineEdit, QaIssue, QaSummary
from rentl_schemas.storage import (
    ArtifactFormat,
    ArtifactMetadata,
    ArtifactRole,
    RunIndexRecord,
    RunStateRecord,
    StorageReference,
)

InputT = TypeVar("InputT", bound=BaseSchema)
OutputT = TypeVar("OutputT", bound=BaseSchema)
PhaseKey = tuple[PhaseName, LanguageCode | None]


class PhaseAgentPool(PhaseAgentPoolProtocol[InputT, OutputT]):
    """Simple concurrent agent pool for phase execution."""

    def __init__(
        self,
        agents: list[PhaseAgentProtocol[InputT, OutputT]],
        max_parallel: int | None = None,
    ) -> None:
        """Initialize the agent pool.

        Args:
            agents: Agent instances used for execution.
            max_parallel: Optional cap on concurrent tasks.

        Raises:
            ValueError: If agents are empty or max_parallel is not positive.
        """
        if not agents:
            raise ValueError("agents must not be empty")
        if max_parallel is not None and max_parallel <= 0:
            raise ValueError("max_parallel must be positive")
        self._agents = agents
        self._max_parallel = max_parallel

    @classmethod
    def from_factory(
        cls,
        factory: Callable[[], PhaseAgentProtocol[InputT, OutputT]],
        count: int,
        max_parallel: int | None = None,
    ) -> PhaseAgentPool[InputT, OutputT]:
        """Create a pool by instantiating agents from a factory.

        Args:
            factory: Callable that creates new agent instances.
            count: Number of agents to create.
            max_parallel: Optional cap on concurrent tasks.

        Returns:
            PhaseAgentPool: Constructed agent pool.

        Raises:
            ValueError: If count is not positive.
        """
        if count <= 0:
            raise ValueError("count must be positive")
        agents = [factory() for _ in range(count)]
        return cls(agents=agents, max_parallel=max_parallel)

    async def run_batch(self, payloads: list[InputT]) -> list[OutputT]:
        """Execute a batch of payloads concurrently.

        Args:
            payloads: Phase input payloads.

        Returns:
            list[OutputT]: Outputs aligned to input order.
        """
        if not payloads:
            return []
        max_parallel = self._max_parallel or len(self._agents)
        max_parallel = min(max_parallel, len(self._agents))
        semaphore = asyncio.Semaphore(max_parallel)
        results: list[OutputT | None] = [None] * len(payloads)

        async def _run(index: int, payload: InputT) -> None:
            agent = self._agents[index % len(self._agents)]
            async with semaphore:
                results[index] = await agent.run(payload)

        async with asyncio.TaskGroup() as group:
            for index, payload in enumerate(payloads):
                group.create_task(_run(index, payload))

        return [cast(OutputT, result) for result in results]


@dataclass(slots=True)
class PipelineRunContext:
    """In-memory run context for orchestration."""

    run_id: RunId
    config: RunConfig
    progress: RunProgress
    created_at: Timestamp
    started_at: Timestamp | None = None
    completed_at: Timestamp | None = None
    status: RunStatus = RunStatus.PENDING
    current_phase: PhaseName | None = None
    last_error: RunError | None = None
    artifacts: list[PhaseArtifacts] = field(default_factory=list)
    source_lines: list[SourceLine] | None = None
    context_output: ContextPhaseOutput | None = None
    pretranslation_output: PretranslationPhaseOutput | None = None
    translate_outputs: dict[LanguageCode, TranslatePhaseOutput] = field(
        default_factory=dict
    )
    qa_outputs: dict[LanguageCode, QaPhaseOutput] = field(default_factory=dict)
    edit_outputs: dict[LanguageCode, EditPhaseOutput] = field(default_factory=dict)
    export_results: dict[LanguageCode, ExportResult] = field(default_factory=dict)
    phase_history: list[PhaseRunRecord] = field(default_factory=list)
    phase_revisions: dict[PhaseKey, int] = field(default_factory=dict)


class PipelineOrchestrator:
    """Pipeline orchestrator for flexible phase execution."""

    def __init__(
        self,
        ingest_adapter: IngestAdapterProtocol | None = None,
        export_adapter: ExportAdapterProtocol | None = None,
        context_agents: ContextAgentPoolProtocol | None = None,
        pretranslation_agents: PretranslationAgentPoolProtocol | None = None,
        translate_agents: TranslateAgentPoolProtocol | None = None,
        qa_agents: QaAgentPoolProtocol | None = None,
        edit_agents: EditAgentPoolProtocol | None = None,
        log_sink: LogSinkProtocol | None = None,
        progress_sink: ProgressSinkProtocol | None = None,
        run_state_store: RunStateStoreProtocol | None = None,
        artifact_store: ArtifactStoreProtocol | None = None,
        clock: Callable[[], Timestamp] | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            ingest_adapter: Adapter for ingest phase.
            export_adapter: Adapter for export phase.
            context_agents: Context agent pool.
            pretranslation_agents: Pretranslation agent pool.
            translate_agents: Translate agent pool.
            qa_agents: QA agent pool.
            edit_agents: Edit agent pool.
            log_sink: Optional log sink.
            progress_sink: Optional progress sink.
            run_state_store: Optional run state store.
            artifact_store: Optional artifact store.
            clock: Optional timestamp provider.
        """
        self._ingest_adapter = ingest_adapter
        self._export_adapter = export_adapter
        self._context_agents = context_agents
        self._pretranslation_agents = pretranslation_agents
        self._translate_agents = translate_agents
        self._qa_agents = qa_agents
        self._edit_agents = edit_agents
        self._log_sink = log_sink
        self._progress_sink = progress_sink
        self._run_state_store = run_state_store
        self._artifact_store = artifact_store
        self._clock = clock or _now_timestamp

    def create_run(self, run_id: RunId, config: RunConfig) -> PipelineRunContext:
        """Create a new run context.

        Args:
            run_id: Run identifier.
            config: Run configuration.

        Returns:
            PipelineRunContext: Initialized run context.
        """
        progress = _build_initial_progress(config)
        return PipelineRunContext(
            run_id=run_id,
            config=config,
            progress=progress,
            created_at=self._clock(),
        )

    async def run_plan(
        self,
        run: PipelineRunContext,
        phases: list[PhaseName] | None = None,
        target_languages: list[LanguageCode] | None = None,
    ) -> None:
        """Run a planned set of phases.

        Args:
            run: Run context.
            phases: Optional ordered phases to execute.
            target_languages: Optional target languages override.
        """
        planned_phases = phases or [
            PhaseName(phase.phase)
            for phase in run.config.pipeline.phases
            if phase.enabled
        ]
        languages = target_languages or run.config.project.languages.target_languages

        run.status = RunStatus.RUNNING
        if run.started_at is None:
            run.started_at = self._clock()
        await self._persist_run_state(run)
        await self._emit_run_progress(run, ProgressEvent.RUN_STARTED)

        await self._emit_log(
            build_run_started_log(self._clock(), run.run_id, planned_phases)
        )
        for phase in planned_phases:
            if phase in {
                PhaseName.TRANSLATE,
                PhaseName.QA,
                PhaseName.EDIT,
                PhaseName.EXPORT,
            }:
                for language in languages:
                    await self.run_phase(run, phase, target_language=language)
            else:
                await self.run_phase(run, phase)
        run.status = RunStatus.COMPLETED
        run.current_phase = None
        run.completed_at = self._clock()
        await self._persist_run_state(run)
        await self._emit_run_progress(run, ProgressEvent.RUN_COMPLETED)
        await self._emit_log(
            build_run_completed_log(self._clock(), run.run_id, RunStatus.COMPLETED)
        )

    async def run_phase(
        self,
        run: PipelineRunContext,
        phase: PhaseName,
        target_language: LanguageCode | None = None,
        ingest_source: IngestSource | None = None,
        export_target: ExportTarget | None = None,
    ) -> PhaseRunRecord:
        """Execute a single phase.

        Args:
            run: Run context.
            phase: Phase name.
            target_language: Target language for language-specific phases.
            ingest_source: Ingest source descriptor for ingest phase.
            export_target: Export target for export phase.

        Returns:
            PhaseRunRecord: Recorded phase run metadata.

        Raises:
            OrchestrationError: If dependencies are missing or the phase is invalid.
        """
        phase_config: PhaseConfig | None = None
        language = target_language
        shard_plan: dict[str, JsonValue] | None = None
        try:
            phase_config = _get_phase_config(run.config, phase)
            if phase_config is None:
                raise OrchestrationError(
                    OrchestrationErrorInfo(
                        code=OrchestrationErrorCode.PHASE_NOT_CONFIGURED,
                        message=f"Phase {phase.value} is not configured",
                        details=OrchestrationErrorDetails(phase=phase),
                    )
                )
            if not phase_config.enabled:
                raise OrchestrationError(
                    OrchestrationErrorInfo(
                        code=OrchestrationErrorCode.PHASE_DISABLED,
                        message=f"Phase {phase.value} is disabled",
                        details=OrchestrationErrorDetails(phase=phase),
                    )
                )
            language = _resolve_target_language(run, phase, target_language)
            _validate_phase_prereqs(run, phase, language)
            shard_plan = _build_shard_plan(
                phase, run.source_lines, phase_config.execution
            )
        except OrchestrationError as exc:
            await self._emit_phase_failure(
                run, phase, exc.info.message, language, exc.info
            )
            raise
        timestamp = self._clock()
        run.status = RunStatus.RUNNING
        if run.started_at is None:
            run.started_at = timestamp
            await self._persist_run_state(run)
            await self._emit_run_progress(run, ProgressEvent.RUN_STARTED)
            await self._emit_log(build_run_started_log(timestamp, run.run_id, [phase]))
        run.current_phase = phase
        self._update_phase_status(run, phase, PhaseStatus.RUNNING, timestamp)
        await self._emit_progress(run, phase, ProgressEvent.PHASE_STARTED)
        await self._emit_log(
            build_phase_log(
                timestamp,
                run.run_id,
                phase,
                PhaseEventSuffix.STARTED,
                "Phase started",
                data=_build_phase_log_data(run, phase, language, shard_plan),
            )
        )

        try:
            if phase == PhaseName.INGEST:
                record = await self._run_ingest(run, ingest_source)
            elif phase == PhaseName.CONTEXT:
                record = await self._run_context(run, phase_config.execution)
            elif phase == PhaseName.PRETRANSLATION:
                record = await self._run_pretranslation(run, phase_config.execution)
            elif phase == PhaseName.TRANSLATE:
                record = await self._run_translate(
                    run, cast(LanguageCode, language), phase_config.execution
                )
            elif phase == PhaseName.QA:
                record = await self._run_qa(
                    run, cast(LanguageCode, language), phase_config.execution
                )
            elif phase == PhaseName.EDIT:
                record = await self._run_edit(
                    run, cast(LanguageCode, language), phase_config.execution
                )
            elif phase == PhaseName.EXPORT:
                record = await self._run_export(
                    run, cast(LanguageCode, language), export_target
                )
            else:
                raise OrchestrationError(
                    OrchestrationErrorInfo(
                        code=OrchestrationErrorCode.INVALID_STATE,
                        message=f"Unsupported phase {phase.value}",
                        details=OrchestrationErrorDetails(phase=phase),
                    )
                )
        except OrchestrationError as exc:
            await self._emit_phase_failure(
                run,
                phase,
                exc.info.message,
                language,
                exc.info,
            )
            raise
        except Exception as exc:
            await self._emit_phase_failure(run, phase, str(exc), language, None)
            raise

        completed_at = self._clock()
        record.started_at = timestamp
        record.completed_at = completed_at
        self._update_phase_status(run, phase, PhaseStatus.COMPLETED, completed_at)
        await self._emit_progress(run, phase, ProgressEvent.PHASE_COMPLETED)
        await self._emit_log(
            build_phase_log(
                completed_at,
                run.run_id,
                phase,
                PhaseEventSuffix.COMPLETED,
                "Phase completed",
                data=_build_phase_log_data(run, phase, language, shard_plan),
            )
        )
        run.current_phase = None
        await self._persist_run_state(run)
        return record

    async def _run_ingest(
        self,
        run: PipelineRunContext,
        ingest_source: IngestSource | None,
    ) -> PhaseRunRecord:
        if self._ingest_adapter is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Ingest adapter is not configured",
                    details=OrchestrationErrorDetails(phase=PhaseName.INGEST),
                )
            )
        if ingest_source is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                    message="Ingest source is required",
                    details=OrchestrationErrorDetails(phase=PhaseName.INGEST),
                )
            )
        run.source_lines = await self._ingest_adapter.load_source(ingest_source)
        artifact_ids = await self._persist_phase_artifact(
            run,
            PhaseName.INGEST,
            run.source_lines,
            None,
            description="Ingest source lines",
        )
        revision = _next_revision(run, PhaseName.INGEST, None)
        dependencies = _build_dependencies(run, PhaseName.INGEST, None)
        record = _build_phase_record(
            run,
            PhaseName.INGEST,
            revision,
            None,
            dependencies=dependencies,
            error=None,
            message="Ingest completed",
        )
        record.artifact_ids = artifact_ids
        run.phase_history.append(record)
        await _update_stale_flags(run, self._log_sink, self._clock)
        return record

    async def _run_context(
        self,
        run: PipelineRunContext,
        execution: PhaseExecutionConfig | None,
    ) -> PhaseRunRecord:
        if self._context_agents is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Context agent pool is not configured",
                    details=OrchestrationErrorDetails(phase=PhaseName.CONTEXT),
                )
            )
        chunks = _build_work_chunks(
            run.source_lines or [], execution, PhaseName.CONTEXT
        )
        inputs = [
            ContextPhaseInput(
                run_id=run.run_id,
                source_lines=chunk.source_lines,
                project_context=None,
                style_guide=None,
                glossary=None,
            )
            for chunk in chunks
        ]
        scene_ids = {
            line.scene_id
            for line in (run.source_lines or [])
            if line.scene_id is not None
        }
        use_scenes = bool(scene_ids)
        total_units = len(scene_ids) if use_scenes else len(run.source_lines or [])
        completed_units = 0
        processed_scenes: set[str] = set()

        async def _on_batch(
            batch_inputs: list[ContextPhaseInput],
            _batch_outputs: list[ContextPhaseOutput],
        ) -> None:
            nonlocal completed_units
            if use_scenes:
                for payload in batch_inputs:
                    for line in payload.source_lines:
                        if line.scene_id is not None:
                            processed_scenes.add(line.scene_id)
                completed_units = len(processed_scenes)
            else:
                completed_units += sum(
                    len(payload.source_lines) for payload in batch_inputs
                )
            await self._emit_phase_progress_update(
                run,
                PhaseName.CONTEXT,
                "scenes_summarized",
                ProgressUnit.SCENES,
                completed_units,
                total_units,
            )

        outputs = await _run_agent_pool(
            self._context_agents,
            inputs,
            execution.max_parallel_agents if execution else None,
            on_batch=_on_batch,
        )
        run.context_output = _merge_context_outputs(run, outputs)
        artifact_ids = await self._persist_phase_artifact(
            run,
            PhaseName.CONTEXT,
            run.context_output,
            None,
            description="Context output",
        )
        revision = _next_revision(run, PhaseName.CONTEXT, None)
        dependencies = _build_dependencies(run, PhaseName.CONTEXT, None)
        record = _build_phase_record(
            run,
            PhaseName.CONTEXT,
            revision,
            None,
            dependencies=dependencies,
            error=None,
            message="Context completed",
        )
        record.artifact_ids = artifact_ids
        run.phase_history.append(record)
        await _update_stale_flags(run, self._log_sink, self._clock)
        return record

    async def _run_pretranslation(
        self,
        run: PipelineRunContext,
        execution: PhaseExecutionConfig | None,
    ) -> PhaseRunRecord:
        if self._pretranslation_agents is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Pretranslation agent pool is not configured",
                    details=OrchestrationErrorDetails(phase=PhaseName.PRETRANSLATION),
                )
            )
        chunks = _build_work_chunks(
            run.source_lines or [], execution, PhaseName.PRETRANSLATION
        )
        inputs = [_build_pretranslation_input(run, chunk) for chunk in chunks]
        total_units = len(run.source_lines or [])
        completed_units = 0

        async def _on_batch(
            batch_inputs: list[PretranslationPhaseInput],
            _batch_outputs: list[PretranslationPhaseOutput],
        ) -> None:
            nonlocal completed_units
            completed_units += sum(
                len(payload.source_lines) for payload in batch_inputs
            )
            await self._emit_phase_progress_update(
                run,
                PhaseName.PRETRANSLATION,
                "lines_annotated",
                ProgressUnit.LINES,
                completed_units,
                total_units,
            )

        outputs = await _run_agent_pool(
            self._pretranslation_agents,
            inputs,
            execution.max_parallel_agents if execution else None,
            on_batch=_on_batch,
        )
        run.pretranslation_output = _merge_pretranslation_outputs(run, outputs)
        artifact_ids = await self._persist_phase_artifact(
            run,
            PhaseName.PRETRANSLATION,
            run.pretranslation_output,
            None,
            description="Pretranslation output",
        )
        revision = _next_revision(run, PhaseName.PRETRANSLATION, None)
        dependencies = _build_dependencies(run, PhaseName.PRETRANSLATION, None)
        record = _build_phase_record(
            run,
            PhaseName.PRETRANSLATION,
            revision,
            None,
            dependencies=dependencies,
            error=None,
            message="Pretranslation completed",
        )
        record.artifact_ids = artifact_ids
        run.phase_history.append(record)
        await _update_stale_flags(run, self._log_sink, self._clock)
        return record

    async def _run_translate(
        self,
        run: PipelineRunContext,
        target_language: LanguageCode,
        execution: PhaseExecutionConfig | None,
    ) -> PhaseRunRecord:
        if self._translate_agents is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Translate agent pool is not configured",
                    details=OrchestrationErrorDetails(
                        phase=PhaseName.TRANSLATE,
                        target_language=target_language,
                    ),
                )
            )
        chunks = _build_work_chunks(
            run.source_lines or [], execution, PhaseName.TRANSLATE
        )
        inputs = [
            _build_translate_input(run, target_language, chunk) for chunk in chunks
        ]
        total_units = len(run.source_lines or [])
        completed_units = 0

        async def _on_batch(
            batch_inputs: list[TranslatePhaseInput],
            _batch_outputs: list[TranslatePhaseOutput],
        ) -> None:
            nonlocal completed_units
            completed_units += sum(
                len(payload.source_lines) for payload in batch_inputs
            )
            await self._emit_phase_progress_update(
                run,
                PhaseName.TRANSLATE,
                "lines_translated",
                ProgressUnit.LINES,
                completed_units,
                total_units,
            )

        outputs = await _run_agent_pool(
            self._translate_agents,
            inputs,
            execution.max_parallel_agents if execution else None,
            on_batch=_on_batch,
        )
        merged_output = _merge_translate_outputs(run, target_language, outputs)
        run.translate_outputs[target_language] = merged_output
        artifact_ids = await self._persist_phase_artifact(
            run,
            PhaseName.TRANSLATE,
            merged_output,
            target_language,
            description=f"Translate output ({target_language})",
        )
        revision = _next_revision(run, PhaseName.TRANSLATE, target_language)
        dependencies = _build_dependencies(run, PhaseName.TRANSLATE, target_language)
        record = _build_phase_record(
            run,
            PhaseName.TRANSLATE,
            revision,
            target_language,
            dependencies=dependencies,
            error=None,
            message="Translate completed",
        )
        record.artifact_ids = artifact_ids
        run.phase_history.append(record)
        await _update_stale_flags(run, self._log_sink, self._clock)
        return record

    async def _run_qa(
        self,
        run: PipelineRunContext,
        target_language: LanguageCode,
        execution: PhaseExecutionConfig | None,
    ) -> PhaseRunRecord:
        if self._qa_agents is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="QA agent pool is not configured",
                    details=OrchestrationErrorDetails(
                        phase=PhaseName.QA,
                        target_language=target_language,
                    ),
                )
            )
        chunks = _build_work_chunks(run.source_lines or [], execution, PhaseName.QA)
        inputs = [_build_qa_input(run, target_language, chunk) for chunk in chunks]
        total_units = len(run.source_lines or [])
        completed_units = 0

        async def _on_batch(
            batch_inputs: list[QaPhaseInput],
            _batch_outputs: list[QaPhaseOutput],
        ) -> None:
            nonlocal completed_units
            completed_units += sum(
                len(payload.source_lines) for payload in batch_inputs
            )
            await self._emit_phase_progress_update(
                run,
                PhaseName.QA,
                "lines_checked",
                ProgressUnit.LINES,
                completed_units,
                total_units,
            )

        outputs = await _run_agent_pool(
            self._qa_agents,
            inputs,
            execution.max_parallel_agents if execution else None,
            on_batch=_on_batch,
        )
        merged_output = _merge_qa_outputs(run, target_language, outputs)
        run.qa_outputs[target_language] = merged_output
        artifact_ids = await self._persist_phase_artifact(
            run,
            PhaseName.QA,
            merged_output,
            target_language,
            description=f"QA output ({target_language})",
        )
        revision = _next_revision(run, PhaseName.QA, target_language)
        dependencies = _build_dependencies(run, PhaseName.QA, target_language)
        record = _build_phase_record(
            run,
            PhaseName.QA,
            revision,
            target_language,
            dependencies=dependencies,
            error=None,
            message="QA completed",
        )
        record.artifact_ids = artifact_ids
        run.phase_history.append(record)
        await _update_stale_flags(run, self._log_sink, self._clock)
        return record

    async def _run_edit(
        self,
        run: PipelineRunContext,
        target_language: LanguageCode,
        execution: PhaseExecutionConfig | None,
    ) -> PhaseRunRecord:
        if self._edit_agents is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Edit agent pool is not configured",
                    details=OrchestrationErrorDetails(
                        phase=PhaseName.EDIT,
                        target_language=target_language,
                    ),
                )
            )
        chunks = _build_work_chunks(run.source_lines or [], execution, PhaseName.EDIT)
        inputs = [_build_edit_input(run, target_language, chunk) for chunk in chunks]
        total_units = len(run.source_lines or [])
        completed_units = 0

        async def _on_batch(
            batch_inputs: list[EditPhaseInput],
            _batch_outputs: list[EditPhaseOutput],
        ) -> None:
            nonlocal completed_units
            completed_units += sum(
                len(payload.translated_lines) for payload in batch_inputs
            )
            await self._emit_phase_progress_update(
                run,
                PhaseName.EDIT,
                "lines_edited",
                ProgressUnit.LINES,
                completed_units,
                total_units,
            )

        outputs = await _run_agent_pool(
            self._edit_agents,
            inputs,
            execution.max_parallel_agents if execution else None,
            on_batch=_on_batch,
        )
        merged_output = _merge_edit_outputs(run, target_language, outputs)
        run.edit_outputs[target_language] = merged_output
        artifact_ids = await self._persist_phase_artifact(
            run,
            PhaseName.EDIT,
            merged_output,
            target_language,
            description=f"Edit output ({target_language})",
        )
        revision = _next_revision(run, PhaseName.EDIT, target_language)
        dependencies = _build_dependencies(run, PhaseName.EDIT, target_language)
        record = _build_phase_record(
            run,
            PhaseName.EDIT,
            revision,
            target_language,
            dependencies=dependencies,
            error=None,
            message="Edit completed",
        )
        record.artifact_ids = artifact_ids
        run.phase_history.append(record)
        await _update_stale_flags(run, self._log_sink, self._clock)
        return record

    async def _run_export(
        self,
        run: PipelineRunContext,
        target_language: LanguageCode,
        export_target: ExportTarget | None,
    ) -> PhaseRunRecord:
        if self._export_adapter is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Export adapter is not configured",
                    details=OrchestrationErrorDetails(
                        phase=PhaseName.EXPORT,
                        target_language=target_language,
                    ),
                )
            )
        if export_target is None:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                    message="Export target is required",
                    details=OrchestrationErrorDetails(
                        phase=PhaseName.EXPORT,
                        target_language=target_language,
                    ),
                )
            )
        translated_lines = _select_export_lines(run, target_language)
        export_result = await self._export_adapter.write_output(
            export_target, translated_lines
        )
        run.export_results[target_language] = export_result
        artifact_ids = await self._persist_phase_artifact(
            run,
            PhaseName.EXPORT,
            export_result,
            target_language,
            description=f"Export result ({target_language})",
        )
        revision = _next_revision(run, PhaseName.EXPORT, target_language)
        dependencies = _build_dependencies(run, PhaseName.EXPORT, target_language)
        record = _build_phase_record(
            run,
            PhaseName.EXPORT,
            revision,
            target_language,
            dependencies=dependencies,
            error=None,
            message="Export completed",
        )
        record.artifact_ids = artifact_ids
        run.phase_history.append(record)
        await _update_stale_flags(run, self._log_sink, self._clock)
        return record

    async def _emit_log(self, entry: LogEntry) -> None:
        if self._log_sink is None:
            return
        await self._log_sink.emit_log(entry)

    async def _emit_run_progress(
        self,
        run: PipelineRunContext,
        event: ProgressEvent,
        timestamp: Timestamp | None = None,
    ) -> None:
        if self._progress_sink is None:
            return
        update = _build_run_progress_update(run, event, timestamp or self._clock())
        await self._progress_sink.emit_progress(update)

    async def _emit_progress(
        self,
        run: PipelineRunContext,
        phase: PhaseName,
        event: ProgressEvent,
        timestamp: Timestamp | None = None,
    ) -> None:
        if self._progress_sink is None:
            return
        update = _build_progress_update(run, phase, event, timestamp or self._clock())
        await self._progress_sink.emit_progress(update)

    async def _emit_phase_progress_update(
        self,
        run: PipelineRunContext,
        phase: PhaseName,
        metric_key: str,
        unit: ProgressUnit,
        completed_units: int,
        total_units: int,
    ) -> None:
        phase_progress = next(
            progress for progress in run.progress.phases if progress.phase == phase
        )
        now = self._clock()
        clamped_completed = min(completed_units, total_units)
        eta_seconds = _estimate_eta_seconds(
            phase_progress.started_at, now, clamped_completed, total_units
        )
        metric = _build_progress_metric(
            metric_key,
            unit,
            clamped_completed,
            total_units,
            eta_seconds,
        )
        phase_progress.metrics = [metric]
        phase_progress.summary = compute_phase_summary(
            [metric], eta_seconds=eta_seconds
        )
        run.progress.summary = compute_run_summary(
            run.progress.phases, run.progress.phase_weights
        )
        await self._emit_progress(run, phase, ProgressEvent.PHASE_PROGRESS, now)

    async def _emit_phase_failure(
        self,
        run: PipelineRunContext,
        phase: PhaseName,
        message: str,
        target_language: LanguageCode | None,
        error_info: OrchestrationErrorInfo | None,
    ) -> None:
        timestamp = self._clock()
        error_code, why, next_action = _build_error_payload(message, error_info)
        event_suffix = PhaseEventSuffix.FAILED
        if error_info and error_info.code in {
            OrchestrationErrorCode.MISSING_DEPENDENCY,
            OrchestrationErrorCode.PHASE_DISABLED,
            OrchestrationErrorCode.PHASE_NOT_CONFIGURED,
        }:
            event_suffix = PhaseEventSuffix.BLOCKED
        run.status = RunStatus.FAILED
        if run.started_at is None:
            run.started_at = timestamp
        run.current_phase = None
        run.completed_at = timestamp
        error_details: dict[str, JsonValue] = {"phase": phase.value}
        if target_language is not None:
            error_details["target_language"] = target_language
        error_details["next_action"] = next_action
        if error_info and error_info.details and error_info.details.missing_phases:
            error_details["missing_phases"] = [
                _normalize_phase_value(phase)
                for phase in error_info.details.missing_phases
            ]
        run.last_error = RunError(
            code=error_code,
            message=message,
            details=error_details,
        )
        self._update_phase_status(run, phase, PhaseStatus.FAILED, timestamp)
        await self._emit_progress(run, phase, ProgressEvent.PHASE_FAILED)
        await self._emit_run_progress(run, ProgressEvent.RUN_FAILED)
        data = _build_phase_log_data(run, phase, target_language)
        data.update({
            "error_code": error_code,
            "why": why,
            "next_action": next_action,
        })
        if error_info and error_info.details and error_info.details.missing_phases:
            data["missing_phases"] = [
                _normalize_phase_value(phase)
                for phase in error_info.details.missing_phases
            ]
        await self._emit_log(
            build_phase_log(
                timestamp,
                run.run_id,
                phase,
                event_suffix,
                message,
                data=data,
            )
        )
        await self._emit_log(
            build_run_failed_log(
                timestamp,
                run.run_id,
                message,
                error_code,
                why,
                next_action,
            )
        )
        await self._persist_run_state(run)

    async def _persist_run_state(self, run: PipelineRunContext) -> None:
        if self._run_state_store is None:
            return
        timestamp = self._clock()
        run_state = _build_run_state(run)
        await self._run_state_store.save_run_state(
            RunStateRecord(
                run_id=run.run_id,
                stored_at=timestamp,
                state=run_state,
                location=None,
                checksum_sha256=None,
            )
        )
        await self._run_state_store.save_run_index(
            _build_run_index_record(run, timestamp)
        )

    async def _persist_phase_artifact(
        self,
        run: PipelineRunContext,
        phase: PhaseName,
        payload: BaseSchema | Sequence[BaseSchema],
        target_language: LanguageCode | None,
        description: str,
    ) -> list[ArtifactId] | None:
        if self._artifact_store is None:
            return None
        payloads = [payload] if isinstance(payload, BaseSchema) else list(payload)
        metadata = ArtifactMetadata(
            artifact_id=uuid7(),
            run_id=run.run_id,
            role=_artifact_role_for_phase(phase),
            phase=phase,
            target_language=target_language,
            format=ArtifactFormat.JSONL,
            created_at=self._clock(),
            location=_placeholder_reference(ArtifactFormat.JSONL),
            description=description,
            size_bytes=None,
            checksum_sha256=None,
            metadata=None,
        )
        try:
            stored = await self._artifact_store.write_artifact_jsonl(metadata, payloads)
        except Exception as exc:
            await self._emit_log(
                build_artifact_persist_failed_log(
                    self._clock(), run.run_id, metadata, str(exc)
                )
            )
            raise
        await self._emit_log(
            build_artifact_persisted_log(self._clock(), run.run_id, stored)
        )
        _record_artifact_reference(run, phase, stored)
        return [stored.artifact_id]

    def _update_phase_status(
        self,
        run: PipelineRunContext,
        phase: PhaseName,
        status: PhaseStatus,
        timestamp: Timestamp,
    ) -> None:
        for phase_progress in run.progress.phases:
            if phase_progress.phase == phase:
                phase_progress.status = status
                if status == PhaseStatus.RUNNING:
                    phase_progress.started_at = timestamp
                if status in {
                    PhaseStatus.COMPLETED,
                    PhaseStatus.FAILED,
                    PhaseStatus.SKIPPED,
                }:
                    phase_progress.completed_at = timestamp
                break
        run.progress.summary = compute_run_summary(
            run.progress.phases, run.progress.phase_weights
        )


def _build_initial_progress(config: RunConfig) -> RunProgress:
    phases = []
    for phase in config.pipeline.phases:
        status = PhaseStatus.PENDING if phase.enabled else PhaseStatus.SKIPPED
        phases.append(
            PhaseProgress(
                phase=PhaseName(phase.phase),
                status=status,
                summary=_blank_progress_summary(),
                metrics=None,
                started_at=None,
                completed_at=None,
            )
        )
    summary = compute_run_summary(phases)
    return RunProgress(phases=phases, summary=summary, phase_weights=None)


def _blank_progress_summary() -> ProgressSummary:
    return ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )


def _build_run_metadata(run: PipelineRunContext) -> RunMetadata:
    return RunMetadata(
        run_id=run.run_id,
        schema_version=run.config.project.schema_version,
        status=run.status,
        current_phase=run.current_phase,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


def _build_run_state(run: PipelineRunContext) -> RunState:
    qa_summary = None
    if run.qa_outputs:
        summaries = [output.summary for output in run.qa_outputs.values()]
        if len(summaries) == 1:
            qa_summary = summaries[0]
    return RunState(
        metadata=_build_run_metadata(run),
        progress=run.progress,
        artifacts=run.artifacts,
        phase_history=run.phase_history or None,
        phase_revisions=_build_phase_revisions(run),
        last_error=run.last_error,
        qa_summary=qa_summary,
    )


def _placeholder_reference(format: ArtifactFormat) -> StorageReference:
    return StorageReference(
        backend=None,
        path=f"placeholder.{format.value}",
        uri=None,
    )


def _artifact_role_for_phase(phase: PhaseName) -> ArtifactRole:
    if phase == PhaseName.EXPORT:
        return ArtifactRole.EXPORT
    return ArtifactRole.PHASE_OUTPUT


def _record_artifact_reference(
    run: PipelineRunContext, phase: PhaseName, stored: ArtifactMetadata
) -> None:
    path = stored.location.path or stored.location.uri or "unknown"
    reference = ArtifactReference(
        artifact_id=stored.artifact_id,
        path=path,
        uri=stored.location.uri,
        format=FileFormat.JSONL,
        created_at=stored.created_at,
        description=stored.description,
    )
    for entry in run.artifacts:
        if entry.phase == phase:
            entry.artifacts.append(reference)
            return
    run.artifacts.append(PhaseArtifacts(phase=phase, artifacts=[reference]))


def _build_run_index_record(
    run: PipelineRunContext, timestamp: Timestamp
) -> RunIndexRecord:
    return RunIndexRecord(
        metadata=_build_run_metadata(run),
        project_name=run.config.project.project_name,
        source_language=run.config.project.languages.source_language,
        target_languages=run.config.project.languages.target_languages,
        updated_at=timestamp,
        progress=run.progress.summary,
        last_error=run.last_error,
    )


def _build_phase_revisions(
    run: PipelineRunContext,
) -> list[PhaseRevision] | None:
    if not run.phase_revisions:
        return None
    revisions = [
        PhaseRevision(
            phase=phase,
            target_language=target_language,
            revision=revision,
        )
        for (phase, target_language), revision in run.phase_revisions.items()
    ]
    revisions.sort(key=lambda entry: (entry.phase.value, entry.target_language or ""))
    return revisions


def _normalize_phase_value(phase: PhaseName | str) -> str:
    return str(phase)


def _now_timestamp() -> Timestamp:
    value = datetime.now(tz=UTC).isoformat()
    return value.replace("+00:00", "Z")


def _get_phase_config(config: RunConfig, phase: PhaseName) -> PhaseConfig | None:
    for entry in config.pipeline.phases:
        if entry.phase == phase:
            return entry
    return None


def _resolve_target_language(
    run: PipelineRunContext,
    phase: PhaseName,
    target_language: LanguageCode | None,
) -> LanguageCode | None:
    if phase not in {
        PhaseName.TRANSLATE,
        PhaseName.QA,
        PhaseName.EDIT,
        PhaseName.EXPORT,
    }:
        return None
    if target_language is not None:
        return target_language
    languages = run.config.project.languages.target_languages
    if len(languages) == 1:
        return languages[0]
    raise OrchestrationError(
        OrchestrationErrorInfo(
            code=OrchestrationErrorCode.MISSING_DEPENDENCY,
            message=f"Target language is required for {phase.value}",
            details=OrchestrationErrorDetails(phase=phase),
        )
    )


def _require_source_lines(run: PipelineRunContext, phase: PhaseName) -> None:
    if not run.source_lines:
        raise OrchestrationError(
            OrchestrationErrorInfo(
                code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                message="Source lines are required",
                details=OrchestrationErrorDetails(
                    phase=phase, missing_phases=[PhaseName.INGEST]
                ),
            )
        )


def _require_translation(
    run: PipelineRunContext,
    target_language: LanguageCode,
    phase: PhaseName,
) -> None:
    if target_language not in run.translate_outputs:
        raise OrchestrationError(
            OrchestrationErrorInfo(
                code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                message="Translation output is required",
                details=OrchestrationErrorDetails(
                    phase=phase,
                    target_language=target_language,
                    missing_phases=[PhaseName.TRANSLATE],
                ),
            )
        )


def _require_context_output(run: PipelineRunContext, phase: PhaseName) -> None:
    if run.context_output is None:
        raise OrchestrationError(
            OrchestrationErrorInfo(
                code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                message="Context output is required",
                details=OrchestrationErrorDetails(
                    phase=phase, missing_phases=[PhaseName.CONTEXT]
                ),
            )
        )


def _require_pretranslation_output(run: PipelineRunContext, phase: PhaseName) -> None:
    if run.pretranslation_output is None:
        raise OrchestrationError(
            OrchestrationErrorInfo(
                code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                message="Pretranslation output is required",
                details=OrchestrationErrorDetails(
                    phase=phase, missing_phases=[PhaseName.PRETRANSLATION]
                ),
            )
        )


def _require_qa_output(
    run: PipelineRunContext, target_language: LanguageCode, phase: PhaseName
) -> None:
    if target_language not in run.qa_outputs:
        raise OrchestrationError(
            OrchestrationErrorInfo(
                code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                message="QA output is required",
                details=OrchestrationErrorDetails(
                    phase=phase,
                    target_language=target_language,
                    missing_phases=[PhaseName.QA],
                ),
            )
        )


def _require_edit_output(
    run: PipelineRunContext, target_language: LanguageCode, phase: PhaseName
) -> None:
    if target_language not in run.edit_outputs:
        raise OrchestrationError(
            OrchestrationErrorInfo(
                code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                message="Edit output is required",
                details=OrchestrationErrorDetails(
                    phase=phase,
                    target_language=target_language,
                    missing_phases=[PhaseName.EDIT],
                ),
            )
        )


def _is_phase_enabled(config: RunConfig, phase: PhaseName) -> bool:
    phase_config = _get_phase_config(config, phase)
    return bool(phase_config and phase_config.enabled)


def _validate_phase_prereqs(
    run: PipelineRunContext,
    phase: PhaseName,
    target_language: LanguageCode | None,
) -> None:
    if phase == PhaseName.INGEST:
        return
    _require_source_lines(run, phase)

    if phase == PhaseName.CONTEXT:
        return

    if _is_phase_enabled(run.config, PhaseName.CONTEXT):
        _require_context_output(run, phase)

    if phase == PhaseName.PRETRANSLATION:
        return

    if phase in {PhaseName.TRANSLATE, PhaseName.EDIT} and _is_phase_enabled(
        run.config, PhaseName.PRETRANSLATION
    ):
        _require_pretranslation_output(run, phase)

    if phase == PhaseName.TRANSLATE:
        return

    if target_language is None:
        raise OrchestrationError(
            OrchestrationErrorInfo(
                code=OrchestrationErrorCode.MISSING_DEPENDENCY,
                message="Target language is required",
                details=OrchestrationErrorDetails(phase=phase),
            )
        )

    if phase in {PhaseName.QA, PhaseName.EDIT, PhaseName.EXPORT}:
        _require_translation(run, target_language, phase)

    if phase == PhaseName.QA:
        return

    if phase == PhaseName.EDIT and _is_phase_enabled(run.config, PhaseName.QA):
        _require_qa_output(run, target_language, phase)

    if phase == PhaseName.EXPORT and _is_phase_enabled(run.config, PhaseName.EDIT):
        _require_edit_output(run, target_language, phase)


def _build_work_chunks(
    source_lines: list[SourceLine],
    execution: PhaseExecutionConfig | None,
    phase: PhaseName,
) -> list[_WorkChunk]:
    if not source_lines:
        return []
    strategy = execution.strategy if execution else PhaseWorkStrategy.FULL
    if strategy == PhaseWorkStrategy.FULL:
        return [_WorkChunk(source_lines=source_lines)]
    if strategy == PhaseWorkStrategy.CHUNK:
        chunk_size = execution.chunk_size if execution else None
        if chunk_size is None:
            return [_WorkChunk(source_lines=source_lines)]
        return [
            _WorkChunk(source_lines=source_lines[index : index + chunk_size])
            for index in range(0, len(source_lines), chunk_size)
        ]
    if strategy == PhaseWorkStrategy.SCENE:
        scene_groups = _group_by_scene(source_lines)
        if execution is None or execution.scene_batch_size is None:
            return [_WorkChunk(source_lines=group) for group in scene_groups]
        batch_size = execution.scene_batch_size
        chunks: list[_WorkChunk] = []
        for index in range(0, len(scene_groups), batch_size):
            batch: list[SourceLine] = []
            for group in scene_groups[index : index + batch_size]:
                batch.extend(group)
            chunks.append(_WorkChunk(source_lines=batch))
        return chunks
    if strategy == PhaseWorkStrategy.ROUTE:
        if any(line.route_id is None for line in source_lines):
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Route strategy requires route_id on all source lines",
                    details=OrchestrationErrorDetails(
                        phase=phase, reason="route_id_missing"
                    ),
                )
            )
        route_groups = _group_by_route(source_lines)
        if execution is None or execution.route_batch_size is None:
            return [_WorkChunk(source_lines=group) for group in route_groups]
        batch_size = execution.route_batch_size
        chunks: list[_WorkChunk] = []
        for index in range(0, len(route_groups), batch_size):
            batch: list[SourceLine] = []
            for group in route_groups[index : index + batch_size]:
                batch.extend(group)
            chunks.append(_WorkChunk(source_lines=batch))
        return chunks
    return [_WorkChunk(source_lines=source_lines)]


def _build_shard_plan(
    phase: PhaseName,
    source_lines: list[SourceLine] | None,
    execution: PhaseExecutionConfig | None,
) -> dict[str, JsonValue] | None:
    if phase not in {
        PhaseName.CONTEXT,
        PhaseName.PRETRANSLATION,
        PhaseName.TRANSLATE,
        PhaseName.QA,
        PhaseName.EDIT,
    }:
        return None
    strategy = execution.strategy if execution else PhaseWorkStrategy.FULL
    strategy_value = getattr(strategy, "value", str(strategy))
    if not source_lines:
        shard_count = 0
    else:
        shard_count = len(_build_work_chunks(source_lines, execution, phase))
    data: dict[str, JsonValue] = {
        "execution_strategy": strategy_value,
        "shard_count": shard_count,
    }
    if execution and execution.max_parallel_agents is not None:
        data["max_parallel_agents"] = execution.max_parallel_agents
    return data


def _group_by_scene(source_lines: list[SourceLine]) -> list[list[SourceLine]]:
    groups: list[list[SourceLine]] = []
    current_group: list[SourceLine] = []
    current_scene = source_lines[0].scene_id
    for line in source_lines:
        if line.scene_id != current_scene and current_group:
            groups.append(current_group)
            current_group = []
        current_scene = line.scene_id
        current_group.append(line)
    if current_group:
        groups.append(current_group)
    return groups


def _group_by_route(source_lines: list[SourceLine]) -> list[list[SourceLine]]:
    groups: list[list[SourceLine]] = []
    current_group: list[SourceLine] = []
    current_route = source_lines[0].route_id
    for line in source_lines:
        if line.route_id != current_route and current_group:
            groups.append(current_group)
            current_group = []
        current_route = line.route_id
        current_group.append(line)
    if current_group:
        groups.append(current_group)
    return groups


@dataclass(slots=True)
class _WorkChunk:
    source_lines: list[SourceLine]

    @property
    def line_ids(self) -> set[LineId]:
        return {line.line_id for line in self.source_lines}

    @property
    def scene_ids(self) -> set[str]:
        return {
            line.scene_id for line in self.source_lines if line.scene_id is not None
        }

    @property
    def route_ids(self) -> set[RouteId]:
        return {
            line.route_id for line in self.source_lines if line.route_id is not None
        }


async def _run_agent_pool(
    pool: PhaseAgentPoolProtocol[InputT, OutputT],
    payloads: list[InputT],
    max_parallel: int | None,
    on_batch: Callable[[list[InputT], list[OutputT]], Awaitable[None]] | None = None,
) -> list[OutputT]:
    if max_parallel is None or max_parallel <= 0 or max_parallel >= len(payloads):
        results = await pool.run_batch(payloads)
        if on_batch is not None:
            await on_batch(payloads, results)
        return results
    results: list[OutputT] = []
    for index in range(0, len(payloads), max_parallel):
        batch = payloads[index : index + max_parallel]
        batch_results = await pool.run_batch(batch)
        results.extend(batch_results)
        if on_batch is not None:
            await on_batch(batch, batch_results)
    return results


def _build_pretranslation_input(
    run: PipelineRunContext, chunk: _WorkChunk
) -> PretranslationPhaseInput:
    scene_summaries = _filter_scene_summaries(run, chunk)
    context_notes = _filter_context_notes(run, chunk)
    project_context = run.context_output.project_context if run.context_output else None
    glossary = run.context_output.glossary if run.context_output else None
    return PretranslationPhaseInput(
        run_id=run.run_id,
        source_lines=chunk.source_lines,
        scene_summaries=scene_summaries,
        context_notes=context_notes,
        project_context=project_context,
        glossary=glossary,
    )


def _build_translate_input(
    run: PipelineRunContext, target_language: LanguageCode, chunk: _WorkChunk
) -> TranslatePhaseInput:
    context_output = run.context_output
    pretranslation_output = run.pretranslation_output
    return TranslatePhaseInput(
        run_id=run.run_id,
        target_language=target_language,
        source_lines=chunk.source_lines,
        scene_summaries=_filter_scene_summaries(run, chunk),
        context_notes=_filter_context_notes(run, chunk),
        project_context=context_output.project_context if context_output else None,
        pretranslation_annotations=_filter_pretranslation_annotations(
            pretranslation_output, chunk
        ),
        term_candidates=pretranslation_output.term_candidates
        if pretranslation_output
        else None,
        glossary=context_output.glossary if context_output else None,
        style_guide=context_output.style_guide if context_output else None,
    )


def _build_qa_input(
    run: PipelineRunContext, target_language: LanguageCode, chunk: _WorkChunk
) -> QaPhaseInput:
    context_output = run.context_output
    translated_lines = _filter_translated_lines(
        run.translate_outputs[target_language].translated_lines, chunk
    )
    return QaPhaseInput(
        run_id=run.run_id,
        target_language=target_language,
        source_lines=chunk.source_lines,
        translated_lines=translated_lines,
        scene_summaries=_filter_scene_summaries(run, chunk),
        context_notes=_filter_context_notes(run, chunk),
        project_context=context_output.project_context if context_output else None,
        glossary=context_output.glossary if context_output else None,
        style_guide=context_output.style_guide if context_output else None,
    )


def _build_edit_input(
    run: PipelineRunContext, target_language: LanguageCode, chunk: _WorkChunk
) -> EditPhaseInput:
    context_output = run.context_output
    pretranslation_output = run.pretranslation_output
    qa_output = run.qa_outputs.get(target_language)
    translated_lines = _filter_translated_lines(
        run.translate_outputs[target_language].translated_lines, chunk
    )
    return EditPhaseInput(
        run_id=run.run_id,
        target_language=target_language,
        translated_lines=translated_lines,
        qa_issues=_filter_qa_issues(qa_output, chunk),
        reviewer_notes=None,
        scene_summaries=_filter_scene_summaries(run, chunk),
        context_notes=_filter_context_notes(run, chunk),
        project_context=context_output.project_context if context_output else None,
        pretranslation_annotations=_filter_pretranslation_annotations(
            pretranslation_output, chunk
        ),
        term_candidates=pretranslation_output.term_candidates
        if pretranslation_output
        else None,
        glossary=context_output.glossary if context_output else None,
        style_guide=context_output.style_guide if context_output else None,
    )


def _filter_scene_summaries(
    run: PipelineRunContext, chunk: _WorkChunk
) -> list[SceneSummary] | None:
    if run.context_output is None:
        return None
    if not chunk.scene_ids:
        return []
    return [
        summary
        for summary in run.context_output.scene_summaries
        if summary.scene_id in chunk.scene_ids
    ]


def _filter_context_notes(
    run: PipelineRunContext, chunk: _WorkChunk
) -> list[ContextNote] | None:
    if run.context_output is None:
        return None
    line_ids = chunk.line_ids
    scene_ids = chunk.scene_ids
    return [
        note
        for note in run.context_output.context_notes
        if (note.line_id in line_ids) or (note.scene_id in scene_ids)
    ]


def _filter_pretranslation_annotations(
    output: PretranslationPhaseOutput | None,
    chunk: _WorkChunk,
) -> list[PretranslationAnnotation] | None:
    if output is None:
        return None
    line_ids = chunk.line_ids
    return [
        annotation
        for annotation in output.annotations
        if annotation.line_id in line_ids
    ]


def _filter_translated_lines(
    translated_lines: list[TranslatedLine],
    chunk: _WorkChunk,
) -> list[TranslatedLine]:
    line_ids = chunk.line_ids
    return [line for line in translated_lines if line.line_id in line_ids]


def _filter_qa_issues(
    output: QaPhaseOutput | None,
    chunk: _WorkChunk,
) -> list[QaIssue] | None:
    if output is None:
        return None
    line_ids = chunk.line_ids
    return [issue for issue in output.issues if issue.line_id in line_ids]


def _merge_context_outputs(
    run: PipelineRunContext, outputs: list[ContextPhaseOutput]
) -> ContextPhaseOutput:
    if not outputs:
        raise OrchestrationError(
            OrchestrationErrorInfo(
                code=OrchestrationErrorCode.INVALID_STATE,
                message="Context output is empty",
                details=OrchestrationErrorDetails(phase=PhaseName.CONTEXT),
            )
        )
    scene_order = _build_scene_index(run.source_lines or [])
    line_order = _build_line_index(run.source_lines or [])
    project_context = _merge_optional_texts([
        output.project_context for output in outputs
    ])
    style_guide = _merge_optional_texts([output.style_guide for output in outputs])
    glossary = _merge_glossary([output.glossary for output in outputs])
    scene_summaries = _merge_scene_summaries(
        [output.scene_summaries for output in outputs], scene_order
    )
    context_notes = _merge_context_notes(
        [output.context_notes for output in outputs], line_order, scene_order
    )
    return ContextPhaseOutput(
        run_id=run.run_id,
        phase=PhaseName.CONTEXT,
        project_context=project_context,
        style_guide=style_guide,
        glossary=glossary,
        scene_summaries=scene_summaries,
        context_notes=context_notes,
    )


def _merge_pretranslation_outputs(
    run: PipelineRunContext, outputs: list[PretranslationPhaseOutput]
) -> PretranslationPhaseOutput:
    line_order = _build_line_index(run.source_lines or [])
    annotations = _merge_annotations(
        [output.annotations for output in outputs], line_order
    )
    term_candidates = _merge_term_candidates([
        output.term_candidates for output in outputs
    ])
    return PretranslationPhaseOutput(
        run_id=run.run_id,
        phase=PhaseName.PRETRANSLATION,
        annotations=annotations,
        term_candidates=term_candidates,
    )


def _merge_translate_outputs(
    run: PipelineRunContext,
    target_language: LanguageCode,
    outputs: list[TranslatePhaseOutput],
) -> TranslatePhaseOutput:
    line_order = _build_line_index(run.source_lines or [])
    translated_lines = _merge_translated_lines(outputs, line_order, target_language)
    return TranslatePhaseOutput(
        run_id=run.run_id,
        phase=PhaseName.TRANSLATE,
        target_language=target_language,
        translated_lines=translated_lines,
    )


def _merge_qa_outputs(
    run: PipelineRunContext,
    target_language: LanguageCode,
    outputs: list[QaPhaseOutput],
) -> QaPhaseOutput:
    line_order = _build_line_index(run.source_lines or [])
    issues = _merge_qa_issues(outputs, line_order, target_language)
    summary = _build_qa_summary(issues)
    return QaPhaseOutput(
        run_id=run.run_id,
        phase=PhaseName.QA,
        target_language=target_language,
        issues=issues,
        summary=summary,
    )


def _merge_edit_outputs(
    run: PipelineRunContext,
    target_language: LanguageCode,
    outputs: list[EditPhaseOutput],
) -> EditPhaseOutput:
    line_order = _build_line_index(run.source_lines or [])
    edited_lines = _merge_edited_lines(outputs, line_order, target_language)
    change_log = _merge_change_log(
        [output.change_log for output in outputs], line_order
    )
    return EditPhaseOutput(
        run_id=run.run_id,
        phase=PhaseName.EDIT,
        target_language=target_language,
        edited_lines=edited_lines,
        change_log=change_log,
    )


def _merge_optional_texts(values: list[str | None]) -> str | None:
    unique = [value for value in values if value]
    if not unique:
        return None
    seen: list[str] = []
    for value in unique:
        if value not in seen:
            seen.append(value)
    return "\n\n".join(seen)


def _merge_glossary(
    glossaries: list[list[GlossaryTerm] | None],
) -> list[GlossaryTerm] | None:
    collected: list[GlossaryTerm] = []
    seen_terms: set[tuple[str, str]] = set()
    for glossary in glossaries:
        if glossary is None:
            continue
        for term in glossary:
            term_key = (term.term, term.translation)
            if term_key in seen_terms:
                continue
            seen_terms.add(term_key)
            collected.append(term)
    if not collected and all(glossary is None for glossary in glossaries):
        return None
    return collected


def _merge_scene_summaries(
    summaries: list[list[SceneSummary]],
    scene_order: dict[str, int],
) -> list[SceneSummary]:
    merged: dict[str, SceneSummary] = {}
    for summary_list in summaries:
        for summary in summary_list:
            merged.setdefault(summary.scene_id, summary)
    return sorted(
        merged.values(),
        key=lambda summary: scene_order.get(summary.scene_id, 10**9),
    )


def _merge_context_notes(
    notes: list[list[ContextNote]],
    line_order: dict[LineId, int],
    scene_order: dict[str, int],
) -> list[ContextNote]:
    merged: dict[NoteId, ContextNote] = {}
    for note_list in notes:
        for note in note_list:
            if note.note_id in merged:
                raise OrchestrationError(
                    OrchestrationErrorInfo(
                        code=OrchestrationErrorCode.INVALID_STATE,
                        message=f"Duplicate context note {note.note_id}",
                        details=OrchestrationErrorDetails(phase=PhaseName.CONTEXT),
                    )
                )
            merged[note.note_id] = note

    def _sort_key(note: ContextNote) -> tuple[int, int]:
        line_index = line_order.get(note.line_id, 10**9) if note.line_id else 10**9
        scene_index = scene_order.get(note.scene_id, 10**9) if note.scene_id else 10**9
        return (line_index, scene_index)

    return sorted(merged.values(), key=_sort_key)


def _merge_annotations(
    annotations: list[list[PretranslationAnnotation]],
    line_order: dict[LineId, int],
) -> list[PretranslationAnnotation]:
    merged: dict[AnnotationId, PretranslationAnnotation] = {}
    for annotation_list in annotations:
        for annotation in annotation_list:
            if annotation.annotation_id in merged:
                raise OrchestrationError(
                    OrchestrationErrorInfo(
                        code=OrchestrationErrorCode.INVALID_STATE,
                        message=f"Duplicate annotation {annotation.annotation_id}",
                        details=OrchestrationErrorDetails(
                            phase=PhaseName.PRETRANSLATION
                        ),
                    )
                )
            merged[annotation.annotation_id] = annotation
    return sorted(
        merged.values(),
        key=lambda annotation: line_order.get(annotation.line_id, 10**9),
    )


def _merge_term_candidates(
    candidates: list[list[TermCandidate]],
) -> list[TermCandidate]:
    merged: dict[str, TermCandidate] = {}
    for candidate_list in candidates:
        for candidate in candidate_list:
            merged.setdefault(candidate.term, candidate)
    return list(merged.values())


def _merge_translated_lines(
    outputs: list[TranslatePhaseOutput],
    line_order: dict[LineId, int],
    target_language: str,
) -> list[TranslatedLine]:
    merged: dict[LineId, TranslatedLine] = {}
    for output in outputs:
        if output.target_language != target_language:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Mismatched target language in translate output",
                    details=OrchestrationErrorDetails(phase=PhaseName.TRANSLATE),
                )
            )
        for line in output.translated_lines:
            if line.line_id in merged:
                raise OrchestrationError(
                    OrchestrationErrorInfo(
                        code=OrchestrationErrorCode.INVALID_STATE,
                        message=f"Duplicate translation line {line.line_id}",
                        details=OrchestrationErrorDetails(phase=PhaseName.TRANSLATE),
                    )
                )
            merged[line.line_id] = line
    return sorted(
        merged.values(),
        key=lambda line: line_order.get(line.line_id, 10**9),
    )


def _merge_qa_issues(
    outputs: list[QaPhaseOutput],
    line_order: dict[LineId, int],
    target_language: LanguageCode,
) -> list[QaIssue]:
    merged: dict[IssueId, QaIssue] = {}
    for output in outputs:
        if output.target_language != target_language:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Mismatched target language in QA output",
                    details=OrchestrationErrorDetails(phase=PhaseName.QA),
                )
            )
        for issue in output.issues:
            if issue.issue_id in merged:
                raise OrchestrationError(
                    OrchestrationErrorInfo(
                        code=OrchestrationErrorCode.INVALID_STATE,
                        message=f"Duplicate QA issue {issue.issue_id}",
                        details=OrchestrationErrorDetails(phase=PhaseName.QA),
                    )
                )
            merged[issue.issue_id] = issue
    return sorted(
        merged.values(),
        key=lambda issue: line_order.get(issue.line_id, 10**9),
    )


def _merge_edited_lines(
    outputs: list[EditPhaseOutput],
    line_order: dict[LineId, int],
    target_language: LanguageCode,
) -> list[TranslatedLine]:
    merged: dict[LineId, TranslatedLine] = {}
    for output in outputs:
        if output.target_language != target_language:
            raise OrchestrationError(
                OrchestrationErrorInfo(
                    code=OrchestrationErrorCode.INVALID_STATE,
                    message="Mismatched target language in edit output",
                    details=OrchestrationErrorDetails(phase=PhaseName.EDIT),
                )
            )
        for line in output.edited_lines:
            if line.line_id in merged:
                raise OrchestrationError(
                    OrchestrationErrorInfo(
                        code=OrchestrationErrorCode.INVALID_STATE,
                        message=f"Duplicate edited line {line.line_id}",
                        details=OrchestrationErrorDetails(phase=PhaseName.EDIT),
                    )
                )
            merged[line.line_id] = line
    return sorted(
        merged.values(),
        key=lambda line: line_order.get(line.line_id, 10**9),
    )


def _merge_change_log(
    change_logs: list[list[LineEdit]],
    line_order: dict[LineId, int],
) -> list[LineEdit]:
    merged: list[LineEdit] = []
    for change_log in change_logs:
        merged.extend(change_log)
    return sorted(
        merged,
        key=lambda entry: line_order.get(entry.line_id, 10**9),
    )


def _build_qa_summary(issues: list[QaIssue]) -> QaSummary:
    by_category: dict[QaCategory, int] = dict.fromkeys(QaCategory, 0)
    by_severity: dict[QaSeverity, int] = dict.fromkeys(QaSeverity, 0)
    for issue in issues:
        by_category[issue.category] += 1
        by_severity[issue.severity] += 1
    return QaSummary(
        total_issues=len(issues),
        by_category=by_category,
        by_severity=by_severity,
    )


def _build_line_index(source_lines: list[SourceLine]) -> dict[LineId, int]:
    return {line.line_id: index for index, line in enumerate(source_lines)}


def _build_scene_index(source_lines: list[SourceLine]) -> dict[str, int]:
    scene_order: dict[str, int] = {}
    for index, line in enumerate(source_lines):
        if line.scene_id is None:
            continue
        if line.scene_id not in scene_order:
            scene_order[line.scene_id] = index
    return scene_order


def _next_revision(
    run: PipelineRunContext,
    phase: PhaseName,
    target_language: LanguageCode | None,
) -> int:
    key = (phase, target_language)
    revision = run.phase_revisions.get(key, 0) + 1
    run.phase_revisions[key] = revision
    return revision


def _build_dependencies(
    run: PipelineRunContext,
    phase: PhaseName,
    target_language: LanguageCode | None,
) -> list[PhaseDependency]:
    dependencies: list[PhaseDependency] = []
    ingest_revision = run.phase_revisions.get((PhaseName.INGEST, None))
    if ingest_revision is not None and phase != PhaseName.INGEST:
        dependencies.append(
            PhaseDependency(
                phase=PhaseName.INGEST,
                revision=ingest_revision,
                target_language=None,
            )
        )
    if phase in {
        PhaseName.PRETRANSLATION,
        PhaseName.TRANSLATE,
        PhaseName.QA,
        PhaseName.EDIT,
    }:
        context_revision = run.phase_revisions.get((PhaseName.CONTEXT, None))
        if context_revision is not None:
            dependencies.append(
                PhaseDependency(
                    phase=PhaseName.CONTEXT,
                    revision=context_revision,
                    target_language=None,
                )
            )
    if phase in {PhaseName.TRANSLATE, PhaseName.EDIT}:
        pretranslation_revision = run.phase_revisions.get((
            PhaseName.PRETRANSLATION,
            None,
        ))
        if pretranslation_revision is not None:
            dependencies.append(
                PhaseDependency(
                    phase=PhaseName.PRETRANSLATION,
                    revision=pretranslation_revision,
                    target_language=None,
                )
            )
    if phase in {PhaseName.QA, PhaseName.EDIT, PhaseName.EXPORT}:
        translate_revision = run.phase_revisions.get((
            PhaseName.TRANSLATE,
            target_language,
        ))
        if translate_revision is not None:
            dependencies.append(
                PhaseDependency(
                    phase=PhaseName.TRANSLATE,
                    revision=translate_revision,
                    target_language=target_language,
                )
            )
    if phase == PhaseName.EDIT:
        qa_revision = run.phase_revisions.get((PhaseName.QA, target_language))
        if qa_revision is not None:
            dependencies.append(
                PhaseDependency(
                    phase=PhaseName.QA,
                    revision=qa_revision,
                    target_language=target_language,
                )
            )
    if phase == PhaseName.EXPORT:
        edit_revision = run.phase_revisions.get((PhaseName.EDIT, target_language))
        if edit_revision is not None:
            dependencies.append(
                PhaseDependency(
                    phase=PhaseName.EDIT,
                    revision=edit_revision,
                    target_language=target_language,
                )
            )
    return dependencies


def _build_phase_record(
    run: PipelineRunContext,
    phase: PhaseName,
    revision: int,
    target_language: LanguageCode | None,
    dependencies: list[PhaseDependency] | None,
    error: RunError | None,
    message: str,
) -> PhaseRunRecord:
    return PhaseRunRecord(
        phase_run_id=uuid7(),
        phase=phase,
        revision=revision,
        status=PhaseStatus.COMPLETED if error is None else PhaseStatus.FAILED,
        target_language=target_language,
        dependencies=dependencies,
        artifact_ids=None,
        started_at=None,
        completed_at=None,
        stale=False,
        error=error,
        message=message,
    )


async def _update_stale_flags(
    run: PipelineRunContext,
    log_sink: LogSinkProtocol | None,
    clock: Callable[[], Timestamp],
) -> None:
    stale_before: dict[tuple[PhaseName, int, str | None], bool] = {
        (record.phase, record.revision, record.target_language): record.stale
        for record in run.phase_history
    }
    for record in run.phase_history:
        record.stale = _is_record_stale(run, record)
    for record in run.phase_history:
        key = (record.phase, record.revision, record.target_language)
        if not record.stale:
            continue
        if stale_before.get(key) is True:
            continue
        if log_sink is None:
            continue
        data = {
            "revision": record.revision,
            "target_language": record.target_language,
        }
        phase_value = PhaseName(record.phase)
        await log_sink.emit_log(
            build_phase_log(
                clock(),
                run.run_id,
                phase_value,
                PhaseEventSuffix.INVALIDATED,
                "Phase output invalidated by upstream changes",
                data=data,
            )
        )


def _is_record_stale(run: PipelineRunContext, record: PhaseRunRecord) -> bool:
    if record.dependencies is None:
        return False
    for dependency in record.dependencies:
        key = (dependency.phase, dependency.target_language)
        latest_revision = run.phase_revisions.get(key)
        if latest_revision is not None and latest_revision > dependency.revision:
            return True
    return False


def _select_export_lines(
    run: PipelineRunContext, target_language: LanguageCode
) -> list[TranslatedLine]:
    if target_language in run.edit_outputs:
        return run.edit_outputs[target_language].edited_lines
    if target_language in run.translate_outputs:
        return run.translate_outputs[target_language].translated_lines
    raise OrchestrationError(
        OrchestrationErrorInfo(
            code=OrchestrationErrorCode.MISSING_DEPENDENCY,
            message="Translated lines required for export",
            details=OrchestrationErrorDetails(
                phase=PhaseName.EXPORT,
                target_language=target_language,
                missing_phases=[PhaseName.TRANSLATE],
            ),
        )
    )


def _build_progress_update(
    run: PipelineRunContext,
    phase: PhaseName,
    event: ProgressEvent,
    timestamp: Timestamp,
) -> ProgressUpdate:
    phase_progress = next(
        progress for progress in run.progress.phases if progress.phase == phase
    )
    phase_status = PhaseStatus(phase_progress.status)
    return ProgressUpdate(
        run_id=run.run_id,
        event=event,
        timestamp=timestamp,
        phase=phase,
        phase_status=phase_status,
        run_progress=run.progress,
        phase_progress=phase_progress,
        metric=None,
        message=None,
    )


def _build_run_progress_update(
    run: PipelineRunContext, event: ProgressEvent, timestamp: Timestamp
) -> ProgressUpdate:
    return ProgressUpdate(
        run_id=run.run_id,
        event=event,
        timestamp=timestamp,
        phase=None,
        phase_status=None,
        run_progress=run.progress,
        phase_progress=None,
        metric=None,
        message=None,
    )


def _parse_timestamp(value: Timestamp) -> datetime:
    return datetime.fromisoformat(value)


def _estimate_eta_seconds(
    started_at: Timestamp | None,
    now: Timestamp,
    completed_units: int,
    total_units: int,
) -> float | None:
    if started_at is None or total_units <= 0 or completed_units <= 0:
        return None
    if completed_units >= total_units:
        return 0.0
    elapsed = (_parse_timestamp(now) - _parse_timestamp(started_at)).total_seconds()
    if elapsed <= 0:
        return None
    rate = completed_units / elapsed
    if rate <= 0:
        return None
    remaining = total_units - completed_units
    return remaining / rate


def _build_progress_metric(
    metric_key: str,
    unit: ProgressUnit,
    completed_units: int,
    total_units: int,
    eta_seconds: float | None,
) -> ProgressMetric:
    clamped_total = max(total_units, 0)
    clamped_completed = max(0, min(completed_units, clamped_total))
    percent_complete = (
        0.0
        if clamped_total == 0
        else min(100.0, (clamped_completed / clamped_total) * 100.0)
    )
    return ProgressMetric(
        metric_key=metric_key,
        unit=unit,
        completed_units=clamped_completed,
        total_units=clamped_total,
        total_status=ProgressTotalStatus.LOCKED,
        percent_complete=percent_complete,
        percent_mode=ProgressPercentMode.FINAL,
        eta_seconds=eta_seconds,
        notes=None,
    )


def _next_action_for_error(error_info: OrchestrationErrorInfo | None) -> str:
    if error_info is None:
        return "Review the run logs and retry."
    error_code = str(error_info.code)
    actions = {
        OrchestrationErrorCode.MISSING_DEPENDENCY.value: (
            "Provide required inputs or complete dependent phases, then retry."
        ),
        OrchestrationErrorCode.PHASE_NOT_CONFIGURED.value: (
            "Enable the phase in the run configuration."
        ),
        OrchestrationErrorCode.PHASE_DISABLED.value: (
            "Enable the phase or remove it from the run configuration."
        ),
        OrchestrationErrorCode.INVALID_STATE.value: (
            "Check the pipeline configuration and current state, then retry."
        ),
        OrchestrationErrorCode.PHASE_EXECUTION_FAILED.value: (
            "Review phase outputs and logs, then retry."
        ),
    }
    return actions.get(error_code, "Review the run logs and retry.")


def _build_error_payload(
    message: str, error_info: OrchestrationErrorInfo | None
) -> tuple[str, str, str]:
    error_code = str(error_info.code) if error_info is not None else "phase_failed"
    why = message
    if error_info and error_info.details and error_info.details.reason:
        why = f"{message} ({error_info.details.reason})"
    next_action = _next_action_for_error(error_info)
    return error_code, why, next_action


def _build_phase_log_data(
    run: PipelineRunContext,
    phase: PhaseName,
    target_language: LanguageCode | None,
    shard_plan: dict[str, JsonValue] | None = None,
) -> dict[str, JsonValue]:
    data: dict[str, JsonValue] = {
        "phase": phase.value,
        "revision": run.phase_revisions.get((phase, target_language)),
    }
    if target_language is not None:
        data["target_language"] = target_language
    if shard_plan:
        data.update(shard_plan)
    return data
