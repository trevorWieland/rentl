"""Unit tests for pipeline orchestrator behavior."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import pytest
from pydantic import Field

from rentl_core.orchestrator import (
    PhaseAgentPool,
    PipelineOrchestrator,
    hydrate_run_context,
)
from rentl_core.ports.orchestrator import (
    LogSinkProtocol,
    OrchestrationError,
    ProgressSinkProtocol,
)
from rentl_core.ports.storage import ArtifactStoreProtocol
from rentl_schemas.base import BaseSchema
from rentl_schemas.config import (
    AgentsConfig,
    CacheConfig,
    ConcurrencyConfig,
    FormatConfig,
    LanguageConfig,
    LoggingConfig,
    LogSinkConfig,
    ModelEndpointConfig,
    ModelSettings,
    PhaseConfig,
    PhaseExecutionConfig,
    PipelineConfig,
    ProjectConfig,
    ProjectPaths,
    RetryConfig,
    RunConfig,
)
from rentl_schemas.events import ProgressEvent, RunEvent
from rentl_schemas.io import IngestSource, SourceLine, TranslatedLine
from rentl_schemas.logs import LogEntry
from rentl_schemas.phases import (
    ContextPhaseInput,
    ContextPhaseOutput,
    EditPhaseInput,
    EditPhaseOutput,
    PretranslationPhaseInput,
    PretranslationPhaseOutput,
    QaPhaseInput,
    QaPhaseOutput,
    SceneSummary,
    TranslatePhaseInput,
    TranslatePhaseOutput,
)
from rentl_schemas.pipeline import PhaseRunRecord, RunMetadata, RunState
from rentl_schemas.primitives import (
    ArtifactId,
    FileFormat,
    LogSinkType,
    PhaseName,
    PhaseStatus,
    PhaseWorkStrategy,
    QaCategory,
    QaSeverity,
    RunId,
    RunStatus,
)
from rentl_schemas.progress import (
    PhaseProgress,
    ProgressPercentMode,
    ProgressSummary,
    ProgressUpdate,
    RunProgress,
)
from rentl_schemas.qa import QaSummary
from rentl_schemas.storage import ArtifactFormat, ArtifactMetadata, ArtifactRole
from rentl_schemas.version import VersionInfo


class _NumberInput(BaseSchema):
    """Simple numeric input schema for pool testing."""

    value: int = Field(..., ge=0, description="Input value")


class _NumberOutput(BaseSchema):
    """Simple numeric output schema for pool testing."""

    value: int = Field(..., ge=0, description="Output value")


class _NumberAgent:
    """Echo agent for pool ordering tests."""

    async def run(self, payload: _NumberInput) -> _NumberOutput:
        return _NumberOutput(value=payload.value)


class _StubIngestAdapter:
    """Stub ingest adapter for orchestrator tests."""

    format = FileFormat.TXT

    def __init__(self, source_lines: list[SourceLine]) -> None:
        self._source_lines = source_lines

    async def load_source(self, source: IngestSource) -> list[SourceLine]:
        return self._source_lines


class _StubContextAgent:
    """Stub context agent for orchestrator tests."""

    async def run(self, payload: ContextPhaseInput) -> ContextPhaseOutput:
        scene_ids = {line.scene_id for line in payload.source_lines if line.scene_id}
        scene_summaries = [
            SceneSummary(scene_id=scene_id, summary="stub", characters=[])
            for scene_id in scene_ids
        ]
        return ContextPhaseOutput(
            run_id=payload.run_id,
            phase=PhaseName.CONTEXT,
            project_context=payload.project_context,
            style_guide=payload.style_guide,
            glossary=payload.glossary,
            scene_summaries=scene_summaries,
            context_notes=[],
        )


class _RecordingContextPool:
    def __init__(self) -> None:
        self.batches: list[list[ContextPhaseInput]] = []

    async def run_batch(
        self, payloads: list[ContextPhaseInput]
    ) -> list[ContextPhaseOutput]:
        self.batches.append(payloads)
        return [
            ContextPhaseOutput(
                run_id=payload.run_id,
                phase=PhaseName.CONTEXT,
                project_context=payload.project_context,
                style_guide=payload.style_guide,
                glossary=payload.glossary,
                scene_summaries=[],
                context_notes=[],
            )
            for payload in payloads
        ]


class _StubTranslateAgent:
    """Stub translate agent for orchestrator tests."""

    async def run(self, payload: TranslatePhaseInput) -> TranslatePhaseOutput:
        translated_lines = [
            TranslatedLine(
                line_id=line.line_id,
                route_id=line.route_id,
                scene_id=line.scene_id,
                speaker=line.speaker,
                source_text=line.text,
                text=f"{payload.target_language}:{line.text}",
                metadata=line.metadata,
                source_columns=line.source_columns,
            )
            for line in payload.source_lines
        ]
        return TranslatePhaseOutput(
            run_id=payload.run_id,
            phase=PhaseName.TRANSLATE,
            target_language=payload.target_language,
            translated_lines=translated_lines,
        )


class _StubPretranslationAgent:
    """Stub pretranslation agent for orchestrator tests."""

    async def run(self, payload: PretranslationPhaseInput) -> PretranslationPhaseOutput:
        return PretranslationPhaseOutput(
            run_id=payload.run_id,
            phase=PhaseName.PRETRANSLATION,
            annotations=[],
            term_candidates=[],
        )


class _StubQaAgent:
    """Stub QA agent for orchestrator tests."""

    async def run(self, payload: QaPhaseInput) -> QaPhaseOutput:
        summary = QaSummary(
            total_issues=0,
            by_category=dict.fromkeys(QaCategory, 0),
            by_severity=dict.fromkeys(QaSeverity, 0),
        )
        return QaPhaseOutput(
            run_id=payload.run_id,
            phase=PhaseName.QA,
            target_language=payload.target_language,
            issues=[],
            summary=summary,
        )


class _StubEditAgent:
    """Stub edit agent that passes all lines through unchanged."""

    async def run(self, payload: EditPhaseInput) -> EditPhaseOutput:
        edited_lines = [
            TranslatedLine(
                line_id=line.line_id,
                route_id=line.route_id,
                scene_id=line.scene_id,
                speaker=line.speaker,
                source_text=line.source_text,
                text=line.text,
                metadata=line.metadata,
                source_columns=line.source_columns,
            )
            for line in payload.translated_lines
        ]
        return EditPhaseOutput(
            run_id=payload.run_id,
            phase=PhaseName.EDIT,
            target_language=payload.target_language,
            edited_lines=edited_lines,
            change_log=[],
        )


class _DroppingEditAgent:
    """Edit agent that drops a line from the output (for validation testing)."""

    async def run(self, payload: EditPhaseInput) -> EditPhaseOutput:
        edited_lines = [
            TranslatedLine(
                line_id=line.line_id,
                route_id=line.route_id,
                scene_id=line.scene_id,
                speaker=line.speaker,
                source_text=line.source_text,
                text=line.text,
                metadata=line.metadata,
                source_columns=line.source_columns,
            )
            for line in payload.translated_lines[:-1]  # drop last line
        ]
        return EditPhaseOutput(
            run_id=payload.run_id,
            phase=PhaseName.EDIT,
            target_language=payload.target_language,
            edited_lines=edited_lines,
            change_log=[],
        )


class _StubLogSink(LogSinkProtocol):
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    async def emit_log(self, entry: LogEntry) -> None:
        self.entries.append(entry)


class _StubProgressSink(ProgressSinkProtocol):
    def __init__(self) -> None:
        self.updates: list[ProgressUpdate] = []

    async def emit_progress(self, update: ProgressUpdate) -> None:
        self.updates.append(update)


class _StubArtifactStore(ArtifactStoreProtocol):
    def __init__(self) -> None:
        self.jsonl_calls: list[tuple[ArtifactMetadata, list[BaseSchema]]] = []

    async def write_artifact_json(
        self, metadata: ArtifactMetadata, payload: BaseSchema
    ) -> ArtifactMetadata:
        raise NotImplementedError("json writes not used in tests")

    async def write_artifact_jsonl(
        self, metadata: ArtifactMetadata, payload: Sequence[BaseSchema]
    ) -> ArtifactMetadata:
        self.jsonl_calls.append((metadata, list(payload)))
        return metadata

    async def list_artifacts(self, run_id: RunId) -> list[ArtifactMetadata]:
        raise NotImplementedError("list not used in tests")

    async def load_artifact_json(
        self, artifact_id: ArtifactId, model: type[BaseSchema]
    ) -> BaseSchema:
        raise NotImplementedError("load json not used in tests")

    async def load_artifact_jsonl(
        self, artifact_id: ArtifactId, model: type[BaseSchema]
    ) -> list[BaseSchema]:
        raise NotImplementedError("load jsonl not used in tests")


def _build_run_config() -> RunConfig:
    project = ProjectConfig(
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        project_name="test",
        paths=ProjectPaths(
            workspace_dir="/tmp",
            input_path="/tmp/input.txt",
            output_dir="/tmp/out",
            logs_dir="/tmp/logs",
        ),
        formats=FormatConfig(input_format=FileFormat.TXT, output_format=FileFormat.TXT),
        languages=LanguageConfig(source_language="en", target_languages=["ja"]),
    )
    pipeline = PipelineConfig(
        default_model=ModelSettings(model_id="gpt-4"),
        phases=[
            PhaseConfig(phase=PhaseName.INGEST),
            PhaseConfig(
                phase=PhaseName.CONTEXT,
                agents=["scene_summarizer"],
            ),
            PhaseConfig(
                phase=PhaseName.PRETRANSLATION,
                agents=["idiom_labeler"],
            ),
            PhaseConfig(
                phase=PhaseName.TRANSLATE,
                agents=["direct_translator"],
            ),
            PhaseConfig(
                phase=PhaseName.QA,
                agents=["style_guide_critic"],
            ),
            PhaseConfig(
                phase=PhaseName.EDIT,
                agents=["basic_editor"],
            ),
            PhaseConfig(phase=PhaseName.EXPORT),
        ],
    )
    return RunConfig(
        project=project,
        logging=LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.NOOP)]),
        agents=_agents_config(),
        endpoint=ModelEndpointConfig(
            provider_name="test",
            base_url="http://localhost",
            api_key_env="TEST_KEY",
        ),
        pipeline=pipeline,
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(),
        cache=CacheConfig(),
    )


def _agents_config() -> AgentsConfig:
    return AgentsConfig(
        prompts_dir="/tmp/prompts",
        agents_dir="/tmp/agents",
    )


def _with_phase_execution(
    config: RunConfig,
    phase_name: PhaseName,
    execution: PhaseExecutionConfig,
) -> RunConfig:
    phases: list[PhaseConfig] = []
    for phase in config.pipeline.phases:
        if phase.phase == phase_name:
            phases.append(phase.model_copy(update={"execution": execution}))
        else:
            phases.append(phase)
    pipeline = config.pipeline.model_copy(update={"phases": phases})
    return config.model_copy(update={"pipeline": pipeline})


def _build_run_state(run_id: RunId) -> RunState:
    summary = ProgressSummary(
        percent_complete=None,
        percent_mode=ProgressPercentMode.UNAVAILABLE,
        eta_seconds=None,
        notes=None,
    )
    progress = RunProgress(
        phases=[
            PhaseProgress(
                phase=PhaseName.INGEST,
                status=PhaseStatus.PENDING,
                summary=summary,
                metrics=None,
                started_at=None,
                completed_at=None,
            )
        ],
        summary=summary,
        phase_weights=None,
    )
    metadata = RunMetadata(
        run_id=run_id,
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        status=RunStatus.COMPLETED,
        current_phase=None,
        created_at="2026-01-27T00:00:00Z",
        started_at="2026-01-27T00:00:01Z",
        completed_at="2026-01-27T00:00:02Z",
    )
    history = [
        PhaseRunRecord(
            phase_run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5d0"),
            phase=PhaseName.TRANSLATE,
            revision=1,
            status=PhaseStatus.COMPLETED,
            target_language="ja",
            dependencies=[],
            artifact_ids=None,
            started_at=None,
            completed_at=None,
            stale=False,
            error=None,
            summary=None,
            message="Translate completed",
        ),
        PhaseRunRecord(
            phase_run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5d1"),
            phase=PhaseName.TRANSLATE,
            revision=2,
            status=PhaseStatus.COMPLETED,
            target_language="ja",
            dependencies=[],
            artifact_ids=None,
            started_at=None,
            completed_at=None,
            stale=False,
            error=None,
            summary=None,
            message="Translate completed",
        ),
    ]
    return RunState(
        metadata=metadata,
        progress=progress,
        artifacts=[],
        phase_history=history,
        phase_revisions=None,
        last_error=None,
        qa_summary=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agent_pool_preserves_order() -> None:
    """Ensure PhaseAgentPool returns outputs in input order."""
    pool = PhaseAgentPool(agents=[_NumberAgent(), _NumberAgent()])
    inputs = [_NumberInput(value=value) for value in [3, 1, 2]]
    outputs = await pool.run_batch(inputs)
    assert [output.value for output in outputs] == [3, 1, 2]


@pytest.mark.unit
def test_hydrate_run_context_restores_phase_revisions() -> None:
    """Hydration restores phase revisions when missing from state."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5d2")
    state = _build_run_state(run_id)
    run = hydrate_run_context(_build_run_config(), state)

    assert run.phase_revisions[PhaseName.TRANSLATE, "ja"] == 2
    assert len(run.phase_history) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_plan_skips_completed_phase() -> None:
    """Completed phase outputs are skipped on resume."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5d9")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            route_id=None,
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]
    pool = _RecordingContextPool()
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        context_agents=[("context_agent", pool)],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)
    run.source_lines = source_lines
    run.context_output = ContextPhaseOutput(
        run_id=run_id,
        phase=PhaseName.CONTEXT,
        project_context=None,
        style_guide=None,
        glossary=None,
        scene_summaries=[],
        context_notes=[],
    )
    run.phase_history.append(
        PhaseRunRecord(
            phase_run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5e0"),
            phase=PhaseName.CONTEXT,
            revision=1,
            status=PhaseStatus.COMPLETED,
            target_language=None,
            dependencies=None,
            artifact_ids=None,
            started_at=None,
            completed_at=None,
            stale=False,
            error=None,
            summary=None,
            message="Context completed",
        )
    )

    await orchestrator.run_plan(run, phases=[PhaseName.CONTEXT])

    assert pool.batches == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_rejects_route_strategy_without_route_ids() -> None:
    """Ensure route strategy fails when route_id is missing."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")
    config = _with_phase_execution(
        _build_run_config(),
        PhaseName.CONTEXT,
        PhaseExecutionConfig(strategy=PhaseWorkStrategy.ROUTE),
    )
    source_lines = [
        SourceLine(
            line_id="line_1",
            route_id=None,
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        context_agents=[("context_agent", _RecordingContextPool())],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    with pytest.raises(OrchestrationError):
        await orchestrator.run_phase(run, PhaseName.CONTEXT)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_routes_sharded_by_route_id() -> None:
    """Ensure route strategy groups work by route_id."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")
    config = _with_phase_execution(
        _build_run_config(),
        PhaseName.CONTEXT,
        PhaseExecutionConfig(strategy=PhaseWorkStrategy.ROUTE),
    )
    source_lines = [
        SourceLine(
            line_id="line_1",
            route_id="route_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_2",
            route_id="route_1",
            scene_id="scene_1",
            speaker=None,
            text="Bye",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_3",
            route_id="route_2",
            scene_id="scene_2",
            speaker=None,
            text="Next",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_4",
            route_id="route_2",
            scene_id="scene_2",
            speaker=None,
            text="Later",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_5",
            route_id="route_3",
            scene_id="scene_3",
            speaker=None,
            text="End",
            metadata=None,
            source_columns=None,
        ),
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    pool = _RecordingContextPool()
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        context_agents=[("context_agent", pool)],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    await orchestrator.run_phase(run, PhaseName.CONTEXT)

    assert len(pool.batches) == 1
    assert len(pool.batches[0]) == 3
    route_ids = [
        {line.route_id for line in payload.source_lines} for payload in pool.batches[0]
    ]
    assert route_ids == [{"route_1"}, {"route_2"}, {"route_3"}]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_blocks_qa_without_translation() -> None:
    """Ensure QA phase blocks when translation is missing."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        qa_agents=[("qa_agent", PhaseAgentPool(agents=[_StubQaAgent()]))],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    await orchestrator.run_phase(run, PhaseName.CONTEXT)
    with pytest.raises(OrchestrationError):
        await orchestrator.run_phase(run, PhaseName.QA, target_language="ja")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_marks_stale_on_upstream_change() -> None:
    """Ensure downstream results become stale after upstream reruns."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_2",
            scene_id="scene_1",
            speaker=None,
            text="Bye",
            metadata=None,
            source_columns=None,
        ),
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        pretranslation_agents=[
            (
                "pretranslation_agent",
                PhaseAgentPool(agents=[_StubPretranslationAgent()]),
            ),
        ],
        translate_agents=[
            ("translate_agent", PhaseAgentPool(agents=[_StubTranslateAgent()])),
        ],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    await orchestrator.run_phase(run, PhaseName.CONTEXT)
    await orchestrator.run_phase(run, PhaseName.PRETRANSLATION)
    await orchestrator.run_phase(run, PhaseName.TRANSLATE, target_language="ja")

    translate_record = next(
        record for record in run.phase_history if record.phase == PhaseName.TRANSLATE
    )
    assert translate_record.phase_run_id is not None
    assert translate_record.stale is False

    await orchestrator.run_phase(run, PhaseName.CONTEXT)
    assert translate_record.stale is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_emits_invalidation_event_on_upstream_change() -> None:
    """Ensure invalidation events are logged when upstream changes."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b4")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_2",
            scene_id="scene_1",
            speaker=None,
            text="Bye",
            metadata=None,
            source_columns=None,
        ),
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    log_sink = _StubLogSink()
    orchestrator = PipelineOrchestrator(
        ingest_adapter=ingest_adapter,
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        pretranslation_agents=[
            (
                "pretranslation_agent",
                PhaseAgentPool(agents=[_StubPretranslationAgent()]),
            ),
        ],
        translate_agents=[
            ("translate_agent", PhaseAgentPool(agents=[_StubTranslateAgent()])),
        ],
        log_sink=log_sink,
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    await orchestrator.run_phase(run, PhaseName.CONTEXT)
    await orchestrator.run_phase(run, PhaseName.PRETRANSLATION)
    await orchestrator.run_phase(run, PhaseName.TRANSLATE, target_language="ja")

    invalidated_before = {
        entry.event for entry in log_sink.entries if entry.event.endswith("invalidated")
    }
    assert "translate_invalidated" not in invalidated_before

    await orchestrator.run_phase(run, PhaseName.CONTEXT)

    invalidated_events = {
        entry.event for entry in log_sink.entries if entry.event.endswith("invalidated")
    }
    assert "translate_invalidated" in invalidated_events


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_blocks_translate_without_pretranslation() -> None:
    """Ensure translate blocks when pretranslation is missing."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        translate_agents=[
            ("translate_agent", PhaseAgentPool(agents=[_StubTranslateAgent()])),
        ],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    await orchestrator.run_phase(run, PhaseName.CONTEXT)
    with pytest.raises(OrchestrationError):
        await orchestrator.run_phase(run, PhaseName.TRANSLATE, target_language="ja")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_blocks_export_without_edit_when_enabled() -> None:
    """Ensure export blocks when edit is enabled but missing."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5b0")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        pretranslation_agents=[
            (
                "pretranslation_agent",
                PhaseAgentPool(agents=[_StubPretranslationAgent()]),
            ),
        ],
        translate_agents=[
            ("translate_agent", PhaseAgentPool(agents=[_StubTranslateAgent()])),
        ],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    await orchestrator.run_phase(run, PhaseName.CONTEXT)
    await orchestrator.run_phase(run, PhaseName.PRETRANSLATION)
    await orchestrator.run_phase(run, PhaseName.TRANSLATE, target_language="ja")
    with pytest.raises(OrchestrationError):
        await orchestrator.run_phase(run, PhaseName.EXPORT, target_language="ja")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_persists_ingest_artifacts() -> None:
    """Ensure ingest artifacts are stored with metadata."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5c1")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    artifact_store = _StubArtifactStore()
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        artifact_store=artifact_store,
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )

    assert len(artifact_store.jsonl_calls) == 1
    metadata, payloads = artifact_store.jsonl_calls[0]
    assert metadata.run_id == run_id
    assert metadata.phase == PhaseName.INGEST
    assert metadata.role == ArtifactRole.PHASE_OUTPUT
    assert metadata.format == ArtifactFormat.JSONL
    assert metadata.target_language is None
    assert metadata.description == "Ingest source lines"
    assert payloads == source_lines
    phase_artifacts = next(
        artifacts for artifacts in run.artifacts if artifacts.phase == PhaseName.INGEST
    )
    assert phase_artifacts.artifacts[0].format == FileFormat.JSONL
    assert phase_artifacts.artifacts[0].description == "Ingest source lines"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_emits_run_started_and_completed_events() -> None:
    """Ensure run start/completion events reach sinks."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5c2")
    config = _build_run_config()
    log_sink = _StubLogSink()
    progress_sink = _StubProgressSink()
    orchestrator = PipelineOrchestrator(
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        log_sink=log_sink,
        progress_sink=progress_sink,
    )
    run = orchestrator.create_run(run_id=run_id, config=config)
    run.source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]

    await orchestrator.run_plan(run, phases=[PhaseName.CONTEXT])

    log_events = {entry.event for entry in log_sink.entries}
    assert RunEvent.STARTED in log_events
    assert RunEvent.COMPLETED in log_events
    progress_events = {update.event for update in progress_sink.updates}
    assert ProgressEvent.RUN_STARTED in progress_events
    assert ProgressEvent.RUN_COMPLETED in progress_events


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_emits_run_failed_events() -> None:
    """Ensure run failure events reach sinks."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5c3")
    config = _build_run_config()
    log_sink = _StubLogSink()
    progress_sink = _StubProgressSink()
    orchestrator = PipelineOrchestrator(
        translate_agents=[
            ("translate_agent", PhaseAgentPool(agents=[_StubTranslateAgent()])),
        ],
        log_sink=log_sink,
        progress_sink=progress_sink,
    )
    run = orchestrator.create_run(run_id=run_id, config=config)
    run.source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]
    run.context_output = ContextPhaseOutput(
        run_id=run_id,
        phase=PhaseName.CONTEXT,
        project_context=None,
        style_guide=None,
        glossary=None,
        scene_summaries=[],
        context_notes=[],
    )

    with pytest.raises(OrchestrationError):
        await orchestrator.run_phase(run, PhaseName.TRANSLATE, target_language="ja")

    log_events = {entry.event for entry in log_sink.entries}
    assert RunEvent.FAILED in log_events
    progress_events = {update.event for update in progress_sink.updates}
    assert ProgressEvent.RUN_FAILED in progress_events


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_records_phase_summary_and_logs() -> None:
    """Ensure phase summaries are recorded and logged on completion."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5d5")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        )
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    log_sink = _StubLogSink()
    orchestrator = PipelineOrchestrator(
        ingest_adapter=ingest_adapter,
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        log_sink=log_sink,
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    record = await orchestrator.run_phase(run, PhaseName.CONTEXT)

    assert record.summary is not None
    metrics = {metric.metric_key: metric.value for metric in record.summary.metrics}
    assert metrics["scene_summary_count"] == 1
    assert metrics["context_note_count"] == 0

    completed_entries = [
        entry for entry in log_sink.entries if entry.event == "context_completed"
    ]
    assert completed_entries
    entry_data = completed_entries[-1].data
    assert entry_data is not None
    summary_payload = entry_data.get("summary")
    assert isinstance(summary_payload, dict)
    assert summary_payload["phase"] == "context"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_validation_gate_passes_on_matching_output() -> None:
    """Edit phase succeeds when output lines match input lines."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5e0")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_2",
            scene_id="scene_1",
            speaker=None,
            text="Bye",
            metadata=None,
            source_columns=None,
        ),
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        pretranslation_agents=[
            (
                "pretranslation_agent",
                PhaseAgentPool(agents=[_StubPretranslationAgent()]),
            ),
        ],
        translate_agents=[
            ("translate_agent", PhaseAgentPool(agents=[_StubTranslateAgent()])),
        ],
        qa_agents=[
            ("qa_agent", PhaseAgentPool(agents=[_StubQaAgent()])),
        ],
        edit_agents=[
            ("edit_agent", PhaseAgentPool(agents=[_StubEditAgent()])),
        ],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    await orchestrator.run_phase(run, PhaseName.CONTEXT)
    await orchestrator.run_phase(run, PhaseName.PRETRANSLATION)
    await orchestrator.run_phase(run, PhaseName.TRANSLATE, target_language="ja")
    await orchestrator.run_phase(run, PhaseName.QA, target_language="ja")
    record = await orchestrator.run_phase(run, PhaseName.EDIT, target_language="ja")

    assert record.status == PhaseStatus.COMPLETED
    assert "ja" in run.edit_outputs
    assert len(run.edit_outputs["ja"].edited_lines) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_validation_gate_rejects_missing_lines() -> None:
    """Edit phase raises when agent drops a line from the output."""
    run_id: RunId = UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5e1")
    config = _build_run_config()
    source_lines = [
        SourceLine(
            line_id="line_1",
            scene_id="scene_1",
            speaker=None,
            text="Hi",
            metadata=None,
            source_columns=None,
        ),
        SourceLine(
            line_id="line_2",
            scene_id="scene_1",
            speaker=None,
            text="Bye",
            metadata=None,
            source_columns=None,
        ),
    ]
    ingest_adapter = _StubIngestAdapter(source_lines)
    orchestrator = PipelineOrchestrator(
        log_sink=_StubLogSink(),
        ingest_adapter=ingest_adapter,
        context_agents=[
            ("context_agent", PhaseAgentPool(agents=[_StubContextAgent()])),
        ],
        pretranslation_agents=[
            (
                "pretranslation_agent",
                PhaseAgentPool(agents=[_StubPretranslationAgent()]),
            ),
        ],
        translate_agents=[
            ("translate_agent", PhaseAgentPool(agents=[_StubTranslateAgent()])),
        ],
        qa_agents=[
            ("qa_agent", PhaseAgentPool(agents=[_StubQaAgent()])),
        ],
        edit_agents=[
            ("edit_agent", PhaseAgentPool(agents=[_DroppingEditAgent()])),
        ],
    )
    run = orchestrator.create_run(run_id=run_id, config=config)

    await orchestrator.run_phase(
        run,
        PhaseName.INGEST,
        ingest_source=IngestSource(input_path="/tmp/input.txt", format=FileFormat.TXT),
    )
    await orchestrator.run_phase(run, PhaseName.CONTEXT)
    await orchestrator.run_phase(run, PhaseName.PRETRANSLATION)
    await orchestrator.run_phase(run, PhaseName.TRANSLATE, target_language="ja")
    await orchestrator.run_phase(run, PhaseName.QA, target_language="ja")

    with pytest.raises(OrchestrationError, match="line count mismatch"):
        await orchestrator.run_phase(run, PhaseName.EDIT, target_language="ja")

    # Output must not be stored on validation failure
    assert "ja" not in run.edit_outputs
