"""Unit tests for agent profile schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rentl_schemas.agents import (
    AgentProfileMeta,
    PhasePromptConfig,
    PromptLayerContent,
    ToolAccessConfig,
)
from rentl_schemas.primitives import PhaseName


def test_tool_access_allows_required_subset() -> None:
    """Required tools are accepted when all are also allowed."""
    config = ToolAccessConfig(
        allowed=["get_game_info", "lookup_context"],
        required=["get_game_info"],
    )
    assert config.required == ["get_game_info"]


def test_tool_access_rejects_required_not_allowed() -> None:
    """Required tools must be present in allowed tools."""
    with pytest.raises(ValidationError):
        ToolAccessConfig(
            allowed=["lookup_context"],
            required=["get_game_info"],
        )


def test_agent_profile_meta_coerces_phase_string() -> None:
    """Ensure AgentProfileMeta coerces phase string to PhaseName."""
    meta = AgentProfileMeta(
        name="scene_summarizer",
        version="1.0.0",
        phase="context",  # type: ignore[arg-type]
        description="Summarizes scenes",
        output_schema="ContextOutput",
    )
    assert meta.phase == PhaseName.CONTEXT


def test_phase_prompt_config_coerces_phase_string() -> None:
    """Ensure PhasePromptConfig coerces phase string to PhaseName."""
    config = PhasePromptConfig(
        phase="translate",  # type: ignore[arg-type]
        system=PromptLayerContent(content="You are a translator."),
    )
    assert config.phase == PhaseName.TRANSLATE
