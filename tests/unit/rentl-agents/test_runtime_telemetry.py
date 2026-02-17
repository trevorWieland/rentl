"""Tests for ProfileAgent telemetry behavior."""

from __future__ import annotations

import asyncio
from uuid import uuid7

from rentl_agents.layers import PromptLayerRegistry
from rentl_agents.runtime import ProfileAgent, ProfileAgentConfig
from rentl_agents.tools.registry import ToolRegistry
from rentl_core.telemetry import AgentTelemetryEmitter
from rentl_io.storage import InMemoryProgressSink
from rentl_schemas.agents import (
    AgentProfileConfig,
    AgentProfileMeta,
    AgentPromptConfig,
    AgentPromptContent,
)
from rentl_schemas.events import ProgressEvent
from rentl_schemas.io import SourceLine
from rentl_schemas.logs import LogEntry
from rentl_schemas.phases import ContextPhaseInput, SceneSummary
from rentl_schemas.primitives import PhaseName, RunId
from rentl_schemas.progress import AgentUsageTotals


class _StubLogSink:
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    async def emit_log(self, entry: LogEntry) -> None:
        self.entries.append(entry)


def _build_profile() -> AgentProfileConfig:
    return AgentProfileConfig(
        meta=AgentProfileMeta(
            name="scene_summarizer",
            version="1.0.0",
            phase=PhaseName.CONTEXT,
            description="Test agent",
            output_schema="SceneSummary",
        ),
        prompts=AgentPromptConfig(
            agent=AgentPromptContent(content="System prompt"),
            user_template=AgentPromptContent(content="User prompt"),
        ),
    )


def _build_payload(run_id: RunId) -> ContextPhaseInput:
    return ContextPhaseInput(
        run_id=run_id,
        source_lines=[
            SourceLine(
                line_id="line_1",
                route_id=None,
                scene_id="scene_1",
                speaker=None,
                text="Hello",
                metadata=None,
                source_columns=None,
            )
        ],
        project_context=None,
        style_guide=None,
        glossary=None,
    )


def _build_agent(
    telemetry_emitter: AgentTelemetryEmitter | None,
    agent_cls: type[ProfileAgent[ContextPhaseInput, SceneSummary]] | None = None,
    required_tool_calls: list[str] | None = None,
) -> ProfileAgent[ContextPhaseInput, SceneSummary]:
    resolved_cls = agent_cls or ProfileAgent
    return resolved_cls(
        profile=_build_profile(),
        output_type=SceneSummary,
        layer_registry=PromptLayerRegistry(),
        tool_registry=ToolRegistry(),
        config=ProfileAgentConfig(
            api_key="test",
            base_url="http://localhost",
            model_id="gpt-5-nano",
            max_retries=1,
            retry_base_delay=0.0,
            required_tool_calls=required_tool_calls,
        ),
        telemetry_emitter=telemetry_emitter,
    )


def test_profile_agent_emits_telemetry_on_success() -> None:
    """ProfileAgent emits start/completed telemetry on success."""
    progress_sink = InMemoryProgressSink()
    log_sink = _StubLogSink()
    emitter = AgentTelemetryEmitter(
        progress_sink=progress_sink,
        log_sink=log_sink,
        clock=lambda: "2026-02-03T12:00:00Z",
    )

    async def _execute_stub(
        _payload: ContextPhaseInput,
    ) -> tuple[SceneSummary, AgentUsageTotals | None]:
        await asyncio.sleep(0)
        return (
            SceneSummary(
                scene_id="scene_1",
                summary="ok",
                characters=["A"],
            ),
            AgentUsageTotals(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                request_count=1,
                tool_calls=0,
            ),
        )

    class StubProfileAgent(ProfileAgent[ContextPhaseInput, SceneSummary]):
        async def _execute(
            self, payload: ContextPhaseInput
        ) -> tuple[SceneSummary, AgentUsageTotals | None]:
            return await _execute_stub(payload)

    agent = _build_agent(emitter, StubProfileAgent)

    payload = _build_payload(uuid7())
    result = asyncio.run(agent.run(payload))
    assert result.scene_id == "scene_1"
    assert [update.event for update in progress_sink.updates] == [
        ProgressEvent.AGENT_STARTED,
        ProgressEvent.AGENT_COMPLETED,
    ]
    started_update = progress_sink.updates[0]
    completed_update = progress_sink.updates[1]
    assert started_update.agent_update is not None
    assert completed_update.agent_update is not None
    assert started_update.agent_update.provider_detected == "local"
    assert started_update.agent_update.endpoint_type == "private"
    assert completed_update.agent_update.provider_detected == "local"
    assert completed_update.agent_update.endpoint_type == "private"
    assert completed_update.agent_update.tool_calls_observed is False
    assert completed_update.agent_update.required_tools_satisfied is None


def test_profile_agent_emits_retry_progress() -> None:
    """ProfileAgent emits retry telemetry between attempts."""
    progress_sink = InMemoryProgressSink()
    emitter = AgentTelemetryEmitter(
        progress_sink=progress_sink,
        log_sink=None,
        clock=lambda: "2026-02-03T12:00:00Z",
    )
    calls: dict[str, int] = {"count": 0}

    async def _execute_stub(
        _payload: ContextPhaseInput,
    ) -> tuple[SceneSummary, AgentUsageTotals | None]:
        await asyncio.sleep(0)
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        return (
            SceneSummary(
                scene_id="scene_1",
                summary="ok",
                characters=["A"],
            ),
            None,
        )

    class StubProfileAgent(ProfileAgent[ContextPhaseInput, SceneSummary]):
        async def _execute(
            self, payload: ContextPhaseInput
        ) -> tuple[SceneSummary, AgentUsageTotals | None]:
            return await _execute_stub(payload)

    agent = _build_agent(emitter, StubProfileAgent)

    payload = _build_payload(uuid7())
    result = asyncio.run(agent.run(payload))
    assert result.scene_id == "scene_1"
    events = [update.event for update in progress_sink.updates]
    assert events == [
        ProgressEvent.AGENT_STARTED,
        ProgressEvent.AGENT_PROGRESS,
        ProgressEvent.AGENT_COMPLETED,
    ]
    retry_update = progress_sink.updates[1]
    assert retry_update.agent_update is not None
    assert retry_update.agent_update.attempt == 2


def test_profile_agent_emits_required_tool_satisfaction_marker() -> None:
    """ProfileAgent marks required tool satisfaction on completion telemetry."""
    progress_sink = InMemoryProgressSink()
    emitter = AgentTelemetryEmitter(
        progress_sink=progress_sink,
        log_sink=None,
        clock=lambda: "2026-02-03T12:00:00Z",
    )

    async def _execute_stub(
        _payload: ContextPhaseInput,
    ) -> tuple[SceneSummary, AgentUsageTotals | None]:
        await asyncio.sleep(0)
        return (
            SceneSummary(
                scene_id="scene_1",
                summary="ok",
                characters=["A"],
            ),
            AgentUsageTotals(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                request_count=1,
                tool_calls=1,
            ),
        )

    class StubProfileAgent(ProfileAgent[ContextPhaseInput, SceneSummary]):
        async def _execute(
            self, payload: ContextPhaseInput
        ) -> tuple[SceneSummary, AgentUsageTotals | None]:
            return await _execute_stub(payload)

    agent = _build_agent(
        emitter,
        StubProfileAgent,
        required_tool_calls=["get_game_info"],
    )

    payload = _build_payload(uuid7())
    result = asyncio.run(agent.run(payload))
    assert result.scene_id == "scene_1"
    completed_update = progress_sink.updates[-1]
    assert completed_update.agent_update is not None
    assert completed_update.agent_update.tool_calls_observed is True
    assert completed_update.agent_update.required_tools_satisfied is True
