"""Tests for ProfileAgent execution wiring and output modes."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.output import PromptedOutput
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


def _agent_shim(mock_agent_cls: MagicMock) -> type:
    class AgentShim:
        @classmethod
        def __class_getitem__(cls, _params: object) -> type:
            return cls

        def __new__(cls, *args: object, **kwargs: object) -> MagicMock:
            return mock_agent_cls(*args, **kwargs)

    return AgentShim


def test_profile_agent_execute_auto_openrouter_uses_prompted_output() -> None:
    """Auto output mode selects PromptedOutput for OpenRouter."""
    profile = _build_profile()
    registry = _build_registry()
    tool_registry = ToolRegistry()
    config = ProfileAgentConfig(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        model_id="gpt-4o-mini",
        output_mode="auto",
        max_requests_per_run=3,
    )
    agent = ProfileAgent(
        profile=profile,
        output_type=SceneSummary,
        layer_registry=registry,
        tool_registry=tool_registry,
        config=config,
    )

    payload = _build_payload()
    mock_result = MagicMock()
    mock_result.output = SceneSummary(
        scene_id="scene_1",
        summary="ok",
        characters=["A"],
    )
    mock_result.usage = MagicMock(
        return_value=RunUsage(input_tokens=1, output_tokens=2, requests=1)
    )
    mock_agent_instance = MagicMock()
    mock_agent_instance.run = AsyncMock(return_value=mock_result)
    mock_agent_cls = MagicMock(return_value=mock_agent_instance)

    with (
        patch("rentl_agents.runtime.OpenRouterProvider") as mock_provider,
        patch("rentl_agents.runtime.OpenAIChatModel"),
        patch("rentl_agents.runtime.Agent", _agent_shim(mock_agent_cls)),
    ):
        result, usage = asyncio.run(agent._execute(payload))

    assert result.scene_id == "scene_1"
    assert usage is not None
    assert mock_provider.called
    call_kwargs = mock_agent_cls.call_args.kwargs
    output_spec = call_kwargs["output_type"]
    assert isinstance(output_spec, PromptedOutput)


def test_profile_agent_execute_tool_mode_sets_prepare_output_tools() -> None:
    """Tool output mode sets prepare_output_tools when required tools are set."""
    profile = _build_profile()
    registry = _build_registry()
    tool_registry = ToolRegistry()
    config = ProfileAgentConfig(
        api_key="test",
        base_url="http://localhost",
        model_id="gpt-4o-mini",
        output_mode="tool",
        required_tool_calls=["get_game_info"],
        max_requests_per_run=2,
    )
    agent = ProfileAgent(
        profile=profile,
        output_type=SceneSummary,
        layer_registry=registry,
        tool_registry=tool_registry,
        config=config,
    )

    payload = _build_payload()
    mock_result = MagicMock()
    mock_result.output = SceneSummary(
        scene_id="scene_2",
        summary="ok",
        characters=["B"],
    )
    mock_result.usage = MagicMock(return_value=RunUsage(requests=1))
    mock_agent_instance = MagicMock()
    mock_agent_instance.run = AsyncMock(return_value=mock_result)
    mock_agent_cls = MagicMock(return_value=mock_agent_instance)

    with (
        patch("rentl_agents.runtime.OpenAIProvider") as mock_provider,
        patch("rentl_agents.runtime.OpenAIChatModel"),
        patch("rentl_agents.runtime.Agent", _agent_shim(mock_agent_cls)),
    ):
        result, usage = asyncio.run(agent._execute(payload))

    assert result.scene_id == "scene_2"
    assert usage is not None
    assert mock_provider.called
    call_kwargs = mock_agent_cls.call_args.kwargs
    assert call_kwargs["output_type"] is SceneSummary
    prepare_output_tools = call_kwargs["prepare_output_tools"]
    assert prepare_output_tools is not None

    tool_defs = [ToolDefinition(name="get_game_info")]
    ctx = type(
        "StubContext",
        (),
        {"messages": [ModelResponse(parts=[ToolCallPart(tool_name="get_game_info")])]},
    )()
    resolved = asyncio.run(prepare_output_tools(ctx, tool_defs))
    assert resolved == tool_defs
