"""Schemas for LLM runtime operations."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.config import OpenRouterProviderRoutingConfig, RetryConfig
from rentl_schemas.primitives import PhaseName, ReasoningEffort


class LlmConnectionStatus(StrEnum):
    """Connectivity check status values."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class LlmEndpointTarget(BaseSchema):
    """Resolved endpoint settings for runtime calls."""

    endpoint_ref: str | None = Field(
        None, description="Endpoint reference label when configured"
    )
    provider_name: str = Field(..., min_length=1, description="Endpoint provider label")
    base_url: str = Field(..., min_length=1, description="Endpoint base URL")
    api_key_env: str = Field(
        ..., min_length=1, description="Environment variable for API key"
    )
    timeout_s: float = Field(..., gt=0, description="Request timeout in seconds")
    openrouter_provider: OpenRouterProviderRoutingConfig | None = Field(
        None,
        description="Optional OpenRouter provider routing controls",
    )


class LlmModelSettings(BaseSchema):
    """LLM model settings derived from config."""

    model_id: str = Field(..., min_length=1, description="Model identifier")
    temperature: float = Field(..., ge=0, le=2, description="Sampling temperature")
    max_output_tokens: int | None = Field(
        None, ge=1, description="Maximum output tokens (None uses model default)"
    )
    reasoning_effort: ReasoningEffort | None = Field(
        None, description="Reasoning effort level when supported"
    )
    top_p: float = Field(..., ge=0, le=1, description="Top-p sampling")
    presence_penalty: float = Field(..., ge=-2, le=2, description="Presence penalty")
    frequency_penalty: float = Field(..., ge=-2, le=2, description="Frequency penalty")


class LlmRuntimeSettings(BaseSchema):
    """Runtime settings for a single LLM invocation."""

    endpoint: LlmEndpointTarget = Field(..., description="Resolved endpoint settings")
    model: LlmModelSettings = Field(..., description="Model settings")
    retry: RetryConfig = Field(..., description="Retry policy")


class LlmPromptRequest(BaseSchema):
    """Prompt request for an LLM runtime call."""

    runtime: LlmRuntimeSettings = Field(..., description="Runtime settings")
    prompt: str = Field(..., min_length=1, description="Prompt text")
    system_prompt: str | None = Field(None, description="Optional system prompt")
    result_schema: type[BaseModel] | None = Field(
        None,
        description="Optional Pydantic schema type for structured output",
        exclude=True,  # Don't serialize this in JSON
    )


class LlmPromptResponse(BaseSchema):
    """Response payload from an LLM runtime call."""

    model_id: str = Field(..., min_length=1, description="Model identifier")
    output_text: str = Field(..., min_length=1, description="Model output")
    structured_output: BaseModel | None = Field(
        None, description="Structured output when result_schema was provided"
    )


class LlmConnectionResult(BaseSchema):
    """Result for a single connectivity check."""

    endpoint_ref: str | None = Field(
        None, description="Endpoint reference label when configured"
    )
    provider_name: str = Field(..., min_length=1, description="Endpoint provider label")
    base_url: str = Field(..., min_length=1, description="Endpoint base URL")
    api_key_env: str = Field(
        ..., min_length=1, description="Environment variable for API key"
    )
    model_id: str | None = Field(None, description="Model identifier")
    phases: list[PhaseName] | None = Field(
        None, description="Phases using this model/endpoint"
    )
    status: LlmConnectionStatus = Field(..., description="Connectivity check status")
    attempts: int = Field(..., ge=0, description="Number of attempts")
    duration_ms: int | None = Field(
        None, ge=0, description="Total duration in milliseconds"
    )
    response_text: str | None = Field(None, description="Response text sample")
    error_message: str | None = Field(None, description="Error message when failed")


class LlmConnectionReport(BaseSchema):
    """Summary of connectivity checks."""

    results: list[LlmConnectionResult] = Field(
        ..., description="Connection check results"
    )
    success_count: int = Field(..., ge=0, description="Successful checks")
    failure_count: int = Field(..., ge=0, description="Failed checks")
    skipped_count: int = Field(..., ge=0, description="Skipped checks")
