"""Unit tests for agent profile schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rentl_schemas.agents import ToolAccessConfig


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
