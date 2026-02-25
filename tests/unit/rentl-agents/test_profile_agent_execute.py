"""Tests for ProfileAgent execution wiring with tool-only output."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid7

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
)
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.usage import RunUsage

from rentl_agents.layers import PromptLayerRegistry
from rentl_agents.runtime import ProfileAgent, ProfileAgentConfig
from rentl_agents.tools.registry import ToolRegistry
from rentl_schemas.agents import (
    AgentProfileConfig,
    AgentProfileMeta,
    AgentPromptConfig,
    AgentPromptContent,
    PhasePromptConfig,
    PromptLayerContent,
    RootPromptConfig,
)
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import ContextPhaseInput, SceneSummary
from rentl_schemas.primitives import PhaseName


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


def _build_registry() -> PromptLayerRegistry:
    registry = PromptLayerRegistry()
    registry.set_root(
        RootPromptConfig(system=PromptLayerContent(content="Root prompt"))
    )
    registry.set_phase(
        PhasePromptConfig(
            phase=PhaseName.CONTEXT,
            system=PromptLayerContent(content="Phase prompt"),
        )
    )
    return registry


def _build_payload() -> ContextPhaseInput:
    return ContextPhaseInput(
        run_id=uuid7(),
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


class _StubAgentRun:
    """Simulates an AgentRun from pydantic-ai Agent.iter()."""

    def __init__(self, output: SceneSummary, run_usage: RunUsage) -> None:
        self._output = output
        self._run_usage = run_usage
        self.result = MagicMock()
        self.result.output = output

    def usage(self) -> RunUsage:
        return self._run_usage

    def all_messages(self) -> list[ModelMessage]:
        return []

    def __aiter__(self) -> _StubAgentRun:
        return self

    async def __anext__(self) -> None:
        raise StopAsyncIteration


def _agent_shim(mock_agent_cls: MagicMock) -> type:
    class AgentShim:
        @classmethod
        def __class_getitem__(cls, _params: tuple[type, ...]) -> type:
            return cls

        def __new__(cls, *args: str, **kwargs: str | int | float | bool) -> MagicMock:
            return mock_agent_cls(*args, **kwargs)

    return AgentShim


def test_profile_agent_execute_openrouter_uses_openrouter_model() -> None:
    """OpenRouter endpoints should use create_model factory with correct params."""
    profile = _build_profile()
    registry = _build_registry()
    config = ProfileAgentConfig(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        model_id="gpt-5-nano",
        max_requests_per_run=3,
    )
    agent = ProfileAgent(
        profile=profile,
        output_type=SceneSummary,
        layer_registry=registry,
        tool_registry=ToolRegistry(),
        config=config,
    )

    payload = _build_payload()
    stub_output = SceneSummary(
        scene_id="scene_1",
        summary="ok",
        characters=["A"],
    )
    run_usage = RunUsage(input_tokens=1, output_tokens=2, requests=1)
    stub_run = _StubAgentRun(stub_output, run_usage)
    iter_captured: dict[str, Any] = {}

    @asynccontextmanager
    async def _iter_stub(  # noqa: RUF029
        *args: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> AsyncIterator[_StubAgentRun]:
        iter_captured.update(kwargs)
        yield stub_run

    mock_agent_instance = MagicMock()
    mock_agent_instance.iter = _iter_stub
    mock_agent_cls = MagicMock(return_value=mock_agent_instance)
    mock_model = MagicMock()
    mock_settings = {"openrouter_provider": {"require_parameters": True}}

    with (
        patch(
            "rentl_agents.runtime.create_model",
            return_value=(mock_model, mock_settings),
        ) as mock_factory,
        patch("rentl_agents.runtime.Agent", _agent_shim(mock_agent_cls)),
    ):
        result, usage = asyncio.run(agent._execute(payload))

    assert result.scene_id == "scene_1"
    assert usage is not None
    mock_factory.assert_called_once()
    assert mock_factory.call_args.kwargs["base_url"] == "https://openrouter.ai/api/v1"

    call_kwargs = mock_agent_cls.call_args.kwargs
    assert call_kwargs["output_type"] is SceneSummary

    model_settings = iter_captured["model_settings"]
    provider_settings = model_settings["openrouter_provider"]
    assert provider_settings["require_parameters"] is True


def test_profile_agent_execute_non_openrouter_uses_openai_model() -> None:
    """Non-OpenRouter endpoints should use create_model factory."""
    profile = _build_profile()
    registry = _build_registry()
    config = ProfileAgentConfig(
        api_key="test",
        base_url="http://localhost:8000/v1",
        model_id="gpt-5-nano",
        max_requests_per_run=3,
    )
    agent = ProfileAgent(
        profile=profile,
        output_type=SceneSummary,
        layer_registry=registry,
        tool_registry=ToolRegistry(),
        config=config,
    )

    payload = _build_payload()
    stub_output = SceneSummary(
        scene_id="scene_2",
        summary="ok",
        characters=["B"],
    )
    run_usage = RunUsage(requests=1)
    stub_run = _StubAgentRun(stub_output, run_usage)

    @asynccontextmanager
    async def _iter_stub(  # noqa: RUF029
        *args: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> AsyncIterator[_StubAgentRun]:
        yield stub_run

    mock_agent_instance = MagicMock()
    mock_agent_instance.iter = _iter_stub
    mock_agent_cls = MagicMock(return_value=mock_agent_instance)
    mock_model = MagicMock()
    mock_settings = {"temperature": 0.7}

    with (
        patch(
            "rentl_agents.runtime.create_model",
            return_value=(mock_model, mock_settings),
        ) as mock_factory,
        patch("rentl_agents.runtime.Agent", _agent_shim(mock_agent_cls)),
    ):
        result, usage = asyncio.run(agent._execute(payload))

    assert result.scene_id == "scene_2"
    assert usage is not None
    mock_factory.assert_called_once()
    assert mock_factory.call_args.kwargs["base_url"] == "http://localhost:8000/v1"
    call_kwargs = mock_agent_cls.call_args.kwargs
    assert call_kwargs["output_type"] is SceneSummary


def test_profile_agent_execute_sets_prepare_output_tools_when_required() -> None:
    """Required tool calls should gate output tools and register recovery."""
    profile = _build_profile()
    registry = _build_registry()
    config = ProfileAgentConfig(
        api_key="test",
        base_url="http://localhost",
        model_id="gpt-5-nano",
        required_tool_calls=["get_game_info"],
        max_requests_per_run=2,
    )
    agent = ProfileAgent(
        profile=profile,
        output_type=SceneSummary,
        layer_registry=registry,
        tool_registry=ToolRegistry(),
        config=config,
    )

    payload = _build_payload()
    stub_output = SceneSummary(
        scene_id="scene_3",
        summary="ok",
        characters=["C"],
    )
    run_usage = RunUsage(requests=1)
    stub_run = _StubAgentRun(stub_output, run_usage)

    @asynccontextmanager
    async def _iter_stub(  # noqa: RUF029
        *args: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> AsyncIterator[_StubAgentRun]:
        yield stub_run

    mock_agent_instance = MagicMock()
    mock_agent_instance.iter = _iter_stub
    # Track @agent.instructions decorator registration
    registered_instructions: list[Any] = []
    mock_agent_instance.instructions.side_effect = lambda fn: (
        registered_instructions.append(fn) or fn
    )
    mock_agent_cls = MagicMock(return_value=mock_agent_instance)
    mock_model = MagicMock()
    mock_settings = {"temperature": 0.7}

    with (
        patch(
            "rentl_agents.runtime.create_model",
            return_value=(mock_model, mock_settings),
        ),
        patch("rentl_agents.runtime.Agent", _agent_shim(mock_agent_cls)),
    ):
        result, usage = asyncio.run(agent._execute(payload))

    assert result.scene_id == "scene_3"
    assert usage is not None

    call_kwargs = mock_agent_cls.call_args.kwargs
    # prepare_output_tools should be set
    prepare_output_tools = call_kwargs["prepare_output_tools"]
    assert prepare_output_tools is not None
    assert call_kwargs["end_strategy"] == "exhaustive"

    # Verify prepare_output_tools works: returns tool defs when required tools called
    tool_defs = [ToolDefinition(name="get_game_info")]
    ctx = type(
        "StubContext",
        (),
        {"messages": [ModelResponse(parts=[ToolCallPart(tool_name="get_game_info")])]},
    )()
    resolved = asyncio.run(prepare_output_tools(ctx, tool_defs))
    assert resolved == tool_defs

    # @agent.instructions recovery function should be registered
    assert len(registered_instructions) == 1


# --- Tests for _required_tools_recovery logic ---


def _make_recovery_fn(
    required: set[str],
) -> Callable[[_StubContext], str | None]:
    """Build a recovery closure matching the runtime @agent.instructions logic.

    Returns:
        A function that inspects message history and returns recovery text
        or None.
    """

    def _required_tools_recovery(ctx: _StubContext) -> str | None:
        has_retries = any(
            isinstance(msg, ModelRequest)
            and any(isinstance(p, RetryPromptPart) for p in msg.parts)
            for msg in ctx.messages
        )
        if not has_retries:
            return None

        called: set[str] = set()
        for msg in ctx.messages:
            if isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart) and part.tool_name in required:
                        called.add(part.tool_name)
        missing = required - called
        if not missing:
            return None

        tool_list = ", ".join(sorted(missing))
        return (
            f"RECOVERY: You have not yet called the required tool(s): "
            f"{tool_list}. You MUST call these tools before you can "
            f"produce your final output. Call them now."
        )

    return _required_tools_recovery


@dataclass
class _StubContext:
    """Minimal context stub with messages list."""

    messages: list[ModelMessage]


def test_required_tools_recovery_returns_none_on_first_request() -> None:
    """No retry messages in history → returns None (no extra instructions)."""
    fn = _make_recovery_fn({"get_game_info"})
    ctx = _StubContext(messages=[])
    assert fn(ctx) is None


def test_required_tools_recovery_returns_guidance_when_tools_missing() -> None:
    """Retry messages present + tool not called → returns guidance string."""
    fn = _make_recovery_fn({"get_game_info"})
    ctx = _StubContext(
        messages=[
            ModelRequest(parts=[RetryPromptPart(content="Please use a tool call")]),
        ]
    )
    result = fn(ctx)
    assert result is not None
    assert "get_game_info" in result
    assert "RECOVERY" in result


def test_required_tools_recovery_returns_none_when_tools_already_called() -> None:
    """Retry messages present + tool already called → returns None."""
    fn = _make_recovery_fn({"get_game_info"})
    ctx = _StubContext(
        messages=[
            ModelResponse(parts=[ToolCallPart(tool_name="get_game_info")]),
            ModelRequest(parts=[RetryPromptPart(content="Please use a tool call")]),
        ]
    )
    assert fn(ctx) is None


def test_required_tools_recovery_lists_only_missing_tools() -> None:
    """When multiple tools required, only missing ones appear in guidance."""
    fn = _make_recovery_fn({"tool_a", "tool_b"})
    ctx = _StubContext(
        messages=[
            ModelResponse(parts=[ToolCallPart(tool_name="tool_a")]),
            ModelRequest(parts=[RetryPromptPart(content="Please use a tool call")]),
        ]
    )
    result = fn(ctx)
    assert result is not None
    assert "tool_b" in result
    assert "tool_a" not in result
