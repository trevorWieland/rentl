"""Configuration schemas for rentl pipelines."""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    PIPELINE_PHASE_ORDER,
    FileFormat,
    JsonValue,
    LanguageCode,
    PhaseName,
    PhaseWorkStrategy,
    ReasoningEffort,
)
from rentl_schemas.version import VersionInfo


class ProjectPaths(BaseSchema):
    """Filesystem locations for project assets."""

    workspace_dir: str = Field(
        ..., min_length=1, description="Project workspace directory"
    )
    input_path: str = Field(..., min_length=1, description="Path to input source file")
    output_dir: str = Field(
        ..., min_length=1, description="Directory for export outputs"
    )
    logs_dir: str = Field(..., min_length=1, description="Directory for JSONL logs")


class FormatConfig(BaseSchema):
    """Input and output formats for the pipeline."""

    input_format: FileFormat = Field(..., description="Input file format")
    output_format: FileFormat = Field(..., description="Output file format")


class LanguageConfig(BaseSchema):
    """Language settings for a run."""

    source_language: LanguageCode = Field(..., description="Source language code")
    target_languages: list[LanguageCode] = Field(
        ..., min_length=1, description="Target language codes"
    )

    @model_validator(mode="after")
    def validate_language_pairs(self) -> LanguageConfig:
        """Ensure target languages are unique and exclude source.

        Returns:
            LanguageConfig: Validated language configuration.

        Raises:
            ValueError: If targets are duplicated or include the source language.
        """
        unique_targets = set(self.target_languages)
        if len(unique_targets) != len(self.target_languages):
            raise ValueError("target_languages must be unique")
        if self.source_language in unique_targets:
            raise ValueError("source_language cannot be in target_languages")
        return self


class ModelEndpointConfig(BaseSchema):
    """BYOK endpoint configuration for OpenAI-compatible APIs."""

    provider_name: str = Field(
        ..., min_length=1, description="User-defined endpoint label"
    )
    base_url: str = Field(..., min_length=1, description="OpenAI-compatible base URL")
    api_key_env: str = Field(
        ..., min_length=1, description="Environment variable for API key"
    )
    timeout_s: float = Field(60.0, gt=0, description="Request timeout in seconds")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        """Ensure base URL uses http/https with a host.

        Args:
            value: Raw base URL string.

        Returns:
            str: Validated base URL.

        Raises:
            ValueError: If the URL is missing scheme/host.
        """
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                "base_url must be an http/https URL with host "
                "(for localhost include http://)"
            )
        if parsed.path in {"", "/"}:
            return f"{value.rstrip('/')}/v1"
        return value


class EndpointSetConfig(BaseSchema):
    """Configuration for multiple BYOK endpoints."""

    default: str = Field(..., min_length=1, description="Default endpoint reference")
    endpoints: list[ModelEndpointConfig] = Field(
        ..., min_length=1, description="Endpoint configurations"
    )

    @model_validator(mode="after")
    def validate_endpoints(self) -> EndpointSetConfig:
        """Validate endpoint uniqueness and default reference.

        Returns:
            EndpointSetConfig: Validated endpoint configuration.

        Raises:
            ValueError: If endpoints are duplicated or default is missing.
        """
        names = [endpoint.provider_name for endpoint in self.endpoints]
        if len(set(names)) != len(names):
            raise ValueError("endpoints must have unique provider_name values")
        if self.default not in names:
            raise ValueError("default must match an endpoint provider_name")
        return self


class ModelSettings(BaseSchema):
    """Per-model settings for agent calls."""

    model_id: str = Field(..., min_length=1, description="Model identifier")
    endpoint_ref: str | None = Field(
        None, min_length=1, description="Endpoint reference override"
    )
    temperature: float = Field(0.2, ge=0, le=2, description="Sampling temperature")
    max_output_tokens: int | None = Field(
        None, ge=1, description="Maximum tokens for responses (None uses model default)"
    )
    reasoning_effort: ReasoningEffort | None = Field(
        None, description="Reasoning effort level when supported"
    )
    top_p: float = Field(1.0, ge=0, le=1, description="Top-p sampling")
    presence_penalty: float = Field(0.0, ge=-2, le=2, description="Presence penalty")
    frequency_penalty: float = Field(0.0, ge=-2, le=2, description="Frequency penalty")


class RetryConfig(BaseSchema):
    """Retry policy for external requests."""

    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")
    backoff_s: float = Field(1.0, gt=0, description="Initial backoff in seconds")
    max_backoff_s: float = Field(
        30.0, gt=0, description="Maximum backoff delay in seconds"
    )


class ConcurrencyConfig(BaseSchema):
    """Concurrency settings for parallel execution."""

    max_parallel_requests: int = Field(
        8, ge=1, description="Max concurrent requests to LLMs"
    )
    max_parallel_scenes: int = Field(
        4, ge=1, description="Max concurrent scene processing"
    )


class CacheConfig(BaseSchema):
    """Disk cache settings for LLM responses."""

    enabled: bool = Field(False, description="Enable disk cache")
    cache_dir: str | None = Field(None, description="Cache directory path")
    ttl_s: int | None = Field(
        None, gt=0, description="Cache entry time-to-live in seconds"
    )
    max_entries: int | None = Field(None, gt=0, description="Maximum cache entries")


class PhaseConfig(BaseSchema):
    """Configuration for a single pipeline phase."""

    phase: PhaseName = Field(..., description="Phase name")
    enabled: bool = Field(True, description="Whether the phase runs")
    model: ModelSettings | None = Field(
        None, description="Phase-specific model settings"
    )
    concurrency: ConcurrencyConfig | None = Field(
        None, description="Phase-specific concurrency overrides"
    )
    retry: RetryConfig | None = Field(
        None, description="Phase-specific retry overrides"
    )
    execution: PhaseExecutionConfig | None = Field(
        None, description="Phase-specific execution and sharding options"
    )
    parameters: dict[str, JsonValue] | None = Field(
        None, description="Phase-specific parameters"
    )


class PhaseExecutionConfig(BaseSchema):
    """Execution settings for phase work sharding and agent fan-out."""

    strategy: PhaseWorkStrategy = Field(
        PhaseWorkStrategy.FULL, description="Work splitting strategy"
    )
    chunk_size: int | None = Field(
        None, gt=0, description="Line count per chunk for chunk strategy"
    )
    scene_batch_size: int | None = Field(
        None, gt=0, description="Scene count per chunk for scene strategy"
    )
    route_batch_size: int | None = Field(
        None, gt=0, description="Route count per chunk for route strategy"
    )
    max_parallel_agents: int | None = Field(
        None, gt=0, description="Maximum parallel agent workers"
    )

    @model_validator(mode="after")
    def validate_strategy(self) -> PhaseExecutionConfig:
        """Validate strategy-specific requirements.

        Returns:
            PhaseExecutionConfig: Validated execution configuration.

        Raises:
            ValueError: If required parameters are missing or conflicting.
        """
        if self.strategy == PhaseWorkStrategy.FULL and (
            self.chunk_size is not None
            or self.scene_batch_size is not None
            or self.route_batch_size is not None
        ):
            raise ValueError(
                "chunk_size/scene_batch_size/route_batch_size not allowed for full"
            )
        if self.strategy == PhaseWorkStrategy.CHUNK and self.chunk_size is None:
            raise ValueError("chunk_size is required for chunk strategy")
        if self.strategy == PhaseWorkStrategy.CHUNK and (
            self.scene_batch_size is not None or self.route_batch_size is not None
        ):
            raise ValueError(
                "scene_batch_size/route_batch_size is only valid for scene/route "
                "strategy"
            )
        if self.strategy == PhaseWorkStrategy.SCENE and (
            self.chunk_size is not None or self.route_batch_size is not None
        ):
            raise ValueError("chunk_size/route_batch_size not allowed for scene")
        if self.strategy == PhaseWorkStrategy.ROUTE and (
            self.chunk_size is not None or self.scene_batch_size is not None
        ):
            raise ValueError("chunk_size/scene_batch_size not allowed for route")
        return self


class PipelineConfig(BaseSchema):
    """Pipeline phase ordering and defaults."""

    default_model: ModelSettings | None = Field(
        None, description="Fallback model settings"
    )
    phases: list[PhaseConfig] = Field(
        ..., min_length=1, description="Ordered pipeline phases"
    )

    @model_validator(mode="after")
    def validate_phases(self) -> PipelineConfig:
        """Validate phase ordering, uniqueness, and required phases.

        Returns:
            PipelineConfig: Validated pipeline configuration.

        Raises:
            ValueError: If phases are duplicated, missing, or out of order.
        """
        phase_names = [phase.phase for phase in self.phases]
        if len(set(phase_names)) != len(phase_names):
            raise ValueError("phases must not contain duplicates")

        required = {
            PhaseName.CONTEXT,
            PhaseName.PRETRANSLATION,
            PhaseName.TRANSLATE,
            PhaseName.QA,
            PhaseName.EDIT,
        }
        missing = required.difference(set(phase_names))
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"missing required phases: {missing_list}")

        order_index = {phase: index for index, phase in enumerate(PIPELINE_PHASE_ORDER)}
        last_index = -1
        for phase_name in phase_names:
            index = order_index.get(phase_name)
            if index is None:
                raise ValueError(f"unsupported phase: {phase_name}")
            if index < last_index:
                raise ValueError("phases must follow canonical order")
            last_index = index

        if self.default_model is None:
            for phase in self.phases:
                if phase.enabled and phase.model is None:
                    raise ValueError("default_model required when phase.model is unset")
        return self


class ProjectConfig(BaseSchema):
    """Project configuration for a pipeline run."""

    schema_version: VersionInfo = Field(..., description="Schema version for config")
    project_name: str = Field(..., min_length=1, description="Project name")
    paths: ProjectPaths = Field(..., description="Project paths")
    formats: FormatConfig = Field(..., description="Input/output formats")
    languages: LanguageConfig = Field(..., description="Language configuration")


class RunConfig(BaseSchema):
    """Top-level configuration for executing a pipeline run."""

    project: ProjectConfig = Field(..., description="Project settings")
    endpoint: ModelEndpointConfig | None = Field(
        None, description="Legacy model endpoint settings"
    )
    endpoints: EndpointSetConfig | None = Field(
        None, description="Multi-endpoint settings"
    )
    pipeline: PipelineConfig = Field(..., description="Pipeline settings")
    concurrency: ConcurrencyConfig = Field(
        ..., description="Global concurrency defaults"
    )
    retry: RetryConfig = Field(..., description="Global retry defaults")
    cache: CacheConfig = Field(..., description="Cache settings")

    @model_validator(mode="after")
    def validate_endpoint_config(self) -> RunConfig:
        """Validate legacy vs multi-endpoint configuration.

        Returns:
            RunConfig: Validated run configuration.

        Raises:
            ValueError: If endpoint configuration is invalid.
        """
        has_legacy = self.endpoint is not None
        has_multi = self.endpoints is not None
        if has_legacy == has_multi:
            raise ValueError("exactly one of endpoint or endpoints must be set")
        endpoint_refs = _collect_endpoint_refs(self.pipeline)
        if has_legacy and endpoint_refs:
            raise ValueError("endpoint_ref requires endpoints configuration")
        if has_multi:
            endpoints = self.endpoints
            if endpoints is None:
                raise ValueError("endpoints configuration is required")
            configured = {entry.provider_name for entry in endpoints.endpoints}
            missing = sorted(ref for ref in endpoint_refs if ref not in configured)
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"Unknown endpoint_ref(s): {joined}")
        return self

    def resolve_endpoint_ref(
        self,
        *,
        model: ModelSettings | None,
        agent_endpoint_ref: str | None = None,
    ) -> str | None:
        """Resolve endpoint references using agent → phase → default precedence.

        Args:
            model: Model settings for the phase (or default model).
            agent_endpoint_ref: Optional per-agent override (future use).

        Returns:
            str | None: Resolved endpoint reference, or None for legacy config.
        """
        if agent_endpoint_ref:
            return agent_endpoint_ref
        if model and model.endpoint_ref:
            return model.endpoint_ref
        if self.endpoints is not None:
            return self.endpoints.default
        return None


def _collect_endpoint_refs(pipeline: PipelineConfig) -> set[str]:
    refs: set[str] = set()
    if pipeline.default_model and pipeline.default_model.endpoint_ref:
        refs.add(pipeline.default_model.endpoint_ref)
    for phase in pipeline.phases:
        if phase.model and phase.model.endpoint_ref:
            refs.add(phase.model.endpoint_ref)
    return refs
