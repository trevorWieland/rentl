"""Tests for ProfileAgent run error handling and retries."""

from __future__ import annotations

import asyncio
from typing import TypedDict
from uuid import uuid7

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded

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


class _AgentArgs(TypedDict):
    profile: AgentProfileConfig
    output_type: type[SceneSummary]
    layer_registry: PromptLayerRegistry
    tool_registry: ToolRegistry
    config: ProfileAgentConfig


def _build_agent_args() -> _AgentArgs:
    return {
        "profile": _build_profile(),
        "output_type": SceneSummary,
        "layer_registry": _build_registry(),
        "tool_registry": ToolRegistry(),
        "config": ProfileAgentConfig(
            api_key="test",
            base_url="http://localhost",
            model_id="gpt-5-nano",
            max_retries=1,
            retry_base_delay=0.0,
        ),
    }


def test_profile_agent_run_raises_on_usage_limit() -> None:
    """UsageLimitExceeded is re-raised for pool-level retry decisions."""

    class UsageLimitAgent(ProfileAgent[ContextPhaseInput, SceneSummary]):
        async def _execute(
            self, payload: ContextPhaseInput
        ) -> tuple[SceneSummary, None]:
            raise UsageLimitExceeded("limit")

    agent = UsageLimitAgent(**_build_agent_args())
    payload = _build_payload()

    with pytest.raises(UsageLimitExceeded):
        asyncio.run(agent.run(payload))


def test_profile_agent_run_raises_on_invalid_output() -> None:
    """UnexpectedModelBehavior is re-raised for pool-level retry decisions."""

    class InvalidOutputAgent(ProfileAgent[ContextPhaseInput, SceneSummary]):
        async def _execute(
            self, payload: ContextPhaseInput
        ) -> tuple[SceneSummary, None]:
            raise UnexpectedModelBehavior("invalid")

    agent = InvalidOutputAgent(**_build_agent_args())
    payload = _build_payload()

    with pytest.raises(UnexpectedModelBehavior):
        asyncio.run(agent.run(payload))


def test_profile_agent_run_retries_on_transient_error() -> None:
    """Transient errors are retried until success."""
    call_count = {"count": 0}

    class RetryAgent(ProfileAgent[ContextPhaseInput, SceneSummary]):
        async def _execute(
            self, payload: ContextPhaseInput
        ) -> tuple[SceneSummary, None]:
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise RuntimeError("transient")
            return (
                SceneSummary(
                    scene_id="scene_1",
                    summary="ok",
                    characters=["A"],
                ),
                None,
            )

    agent = RetryAgent(**_build_agent_args())
    payload = _build_payload()
    result = asyncio.run(agent.run(payload))

    assert result.scene_id == "scene_1"
    assert call_count["count"] == 2


def test_profile_agent_run_raises_on_wall_clock_timeout() -> None:
    """RuntimeError is raised when run_timeout_s wall-clock budget is exceeded."""

    class HangingAgent(ProfileAgent[ContextPhaseInput, SceneSummary]):
        async def _execute(
            self, payload: ContextPhaseInput
        ) -> tuple[SceneSummary, None]:
            await asyncio.sleep(10)
            return (
                SceneSummary(
                    scene_id="scene_1",
                    summary="ok",
                    characters=["A"],
                ),
                None,
            )

    args = _build_agent_args()
    args["config"] = ProfileAgentConfig(
        api_key="test",
        base_url="http://localhost",
        model_id="gpt-5-nano",
        max_retries=0,
        retry_base_delay=0.0,
        run_timeout_s=0.05,
    )
    agent = HangingAgent(**args)
    payload = _build_payload()

    with pytest.raises(RuntimeError, match="wall-clock budget"):
        asyncio.run(agent.run(payload))


def test_profile_agent_run_no_timeout_when_budget_none() -> None:
    """Agent runs normally when run_timeout_s is not set."""

    class QuickAgent(ProfileAgent[ContextPhaseInput, SceneSummary]):
        async def _execute(
            self, payload: ContextPhaseInput
        ) -> tuple[SceneSummary, None]:
            return (
                SceneSummary(
                    scene_id="scene_1",
                    summary="ok",
                    characters=["A"],
                ),
                None,
            )

    args = _build_agent_args()
    # Explicitly confirm run_timeout_s defaults to None
    assert args["config"].run_timeout_s is None
    agent = QuickAgent(**args)
    payload = _build_payload()
    result = asyncio.run(agent.run(payload))

    assert result.scene_id == "scene_1"
