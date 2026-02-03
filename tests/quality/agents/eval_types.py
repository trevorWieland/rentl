"""Shared data models for quality agent evals."""

from __future__ import annotations

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import JsonValue


class ToolCallRecord(BaseSchema):
    """Recorded tool call for evaluation."""

    tool_name: str = Field(..., min_length=1, description="Tool name")
    args: dict[str, JsonValue] = Field(
        default_factory=dict, description="Tool input arguments"
    )
    result: dict[str, JsonValue] = Field(
        default_factory=dict, description="Tool output payload"
    )


class AgentEvalOutput(BaseSchema):
    """Normalized output for agent evaluation."""

    output_text: str = Field(..., min_length=1, description="Text for LLM judging")
    output_data: dict[str, JsonValue] = Field(
        default_factory=dict, description="Structured output payload"
    )
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list, description="Recorded tool calls"
    )
