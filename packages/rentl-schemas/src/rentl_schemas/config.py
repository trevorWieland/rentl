"""Configuration schemas for rentl pipelines."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import (
    PIPELINE_PHASE_ORDER,
    FileFormat,
    JsonValue,
    LanguageCode,
    LogSinkType,
    PhaseName,
    PhaseWorkStrategy,
    QaSeverity,
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


class LogSinkConfig(BaseSchema):
    """Configuration for a single log sink."""

    type: LogSinkType = Field(..., description="Log sink type (console|file|noop)")

    @field_validator("type", mode="before")
    @classmethod
    def _coerce_type(cls, value: object) -> LogSinkType:
        if isinstance(value, LogSinkType):
            return value
        if isinstance(value, str):
            return LogSinkType(value)
        return value  # type: ignore[return-value]


class LoggingConfig(BaseSchema):
    """Logging configuration for pipeline runs and CLI commands."""

    sinks: list[LogSinkConfig] = Field(
        ..., min_length=1, description="Log sinks to enable"
    )

    @model_validator(mode="after")
    def validate_sink_types(self) -> LoggingConfig:
        """Ensure log sink types are unique.

        Returns:
            LoggingConfig: Validated logging configuration.

        Raises:
            ValueError: If sink types are duplicated.
        """
        sink_types = [sink.type for sink in self.sinks]
        if len(set(sink_types)) != len(sink_types):
            raise ValueError("log sinks must not contain duplicates")
        return self


class FormatConfig(BaseSchema):
    """Input and output formats for the pipeline."""

    input_format: FileFormat = Field(..., description="Input file format")
    output_format: FileFormat = Field(..., description="Output file format")

    @field_validator("input_format", "output_format", mode="before")
    @classmethod
    def _coerce_format(cls, value: object) -> FileFormat:
        if isinstance(value, FileFormat):
            return value
        if isinstance(value, str):
            return FileFormat(value)
        return value  # type: ignore[return-value]


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


class OpenRouterMaxPriceConfig(BaseSchema):
    """OpenRouter max price routing controls (USD per million tokens)."""

    prompt: int | None = Field(
        None,
        ge=0,
        description="Maximum prompt token price in USD per million tokens",
    )
    completion: int | None = Field(
        None,
        ge=0,
        description="Maximum completion token price in USD per million tokens",
    )
    image: int | None = Field(
        None,
        ge=0,
        description="Maximum image token price in USD per million tokens",
    )
    audio: int | None = Field(
        None,
        ge=0,
        description="Maximum audio token price in USD per million tokens",
    )
    request: int | None = Field(
        None,
        ge=0,
        description="Maximum per-request price in USD per million requests",
    )


OpenRouterProviderSort = Literal["price", "throughput", "latency"]
OpenRouterDataCollection = Literal["allow", "deny"]
OpenRouterQuantization = Literal[
    "int4", "int8", "fp4", "fp6", "fp8", "fp16", "bf16", "fp32", "unknown"
]


class OpenRouterProviderRoutingConfig(BaseSchema):
    """OpenRouter provider routing constraints for request execution."""

    order: list[str] | None = Field(
        None,
        description="Preferred provider slugs in routing order",
    )
    allow_fallbacks: bool | None = Field(
        None,
        description="Whether OpenRouter may fallback to backup providers",
    )
    require_parameters: bool = Field(
        True,
        description="Require routed providers to support all request parameters",
    )
    data_collection: OpenRouterDataCollection | None = Field(
        None,
        description="Restrict routing by provider data collection policy",
    )
    zdr: bool | None = Field(
        None,
        description="Restrict routing to zero-data-retention providers",
    )
    only: list[str] | None = Field(
        None,
        description="Allowlist of provider slugs for routing",
    )
    ignore: list[str] | None = Field(
        None,
        description="Provider slugs to exclude from routing",
    )
    quantizations: list[OpenRouterQuantization] | None = Field(
        None,
        description="Allowed model quantizations for routed providers",
    )
    sort: OpenRouterProviderSort | None = Field(
        None,
        description="Provider sort strategy for routing",
    )
    max_price: OpenRouterMaxPriceConfig | None = Field(
        None,
        description="Maximum provider price constraints",
    )

    @model_validator(mode="after")
    def validate_provider_sets(self) -> OpenRouterProviderRoutingConfig:
        """Validate allow/ignore provider set consistency.

        Returns:
            OpenRouterProviderRoutingConfig: Validated routing configuration.

        Raises:
            ValueError: If only/ignore provider sets overlap.
        """
        only_set = set(self.only or [])
        ignore_set = set(self.ignore or [])
        overlap = sorted(only_set.intersection(ignore_set))
        if overlap:
            joined = ", ".join(overlap)
            raise ValueError(
                f"openrouter provider sets overlap in only/ignore: {joined}"
            )
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
    openrouter_provider: OpenRouterProviderRoutingConfig | None = Field(
        None,
        description="OpenRouter provider routing controls",
    )

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

    @model_validator(mode="after")
    def validate_openrouter_provider(self) -> ModelEndpointConfig:
        """Validate OpenRouter-only routing configuration usage.

        Returns:
            ModelEndpointConfig: Validated endpoint configuration.

        Raises:
            ValueError: If OpenRouter routing config is invalid for this endpoint.
        """
        is_openrouter = "openrouter.ai" in self.base_url.lower()
        if self.openrouter_provider is not None and not is_openrouter:
            raise ValueError(
                "openrouter_provider is only valid for OpenRouter endpoints"
            )
        if is_openrouter and self.openrouter_provider is None:
            self.openrouter_provider = OpenRouterProviderRoutingConfig(
                require_parameters=True
            )
        if (
            is_openrouter
            and self.openrouter_provider is not None
            and not self.openrouter_provider.require_parameters
        ):
            raise ValueError(
                "openrouter_provider.require_parameters must be true "
                "for tool-only runtime"
            )
        return self


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
        4096,
        ge=1,
        description="Maximum tokens for responses (defaults to 4096)",
    )
    reasoning_effort: ReasoningEffort | None = Field(
        None, description="Reasoning effort level when supported"
    )
    top_p: float = Field(1.0, ge=0, le=1, description="Top-p sampling")
    presence_penalty: float = Field(0.0, ge=-2, le=2, description="Presence penalty")
    frequency_penalty: float = Field(0.0, ge=-2, le=2, description="Frequency penalty")

    @field_validator("reasoning_effort", mode="before")
    @classmethod
    def _coerce_reasoning_effort(cls, value: object) -> ReasoningEffort | None:
        if value is None:
            return None
        if isinstance(value, ReasoningEffort):
            return value
        if isinstance(value, str):
            return ReasoningEffort(value)
        return value  # type: ignore[return-value]


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


class AgentsConfig(BaseSchema):
    """Agent discovery and prompt configuration."""

    prompts_dir: str = Field(..., min_length=1, description="Prompts directory")
    agents_dir: str = Field(..., min_length=1, description="Agents directory")


class PhaseConfig(BaseSchema):
    """Configuration for a single pipeline phase."""

    phase: PhaseName = Field(..., description="Phase name")
    enabled: bool = Field(True, description="Whether the phase runs")
    agents: list[str] | None = Field(
        None,
        min_length=1,
        description="Ordered agent names to execute for this phase",
    )
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

    @field_validator("phase", mode="before")
    @classmethod
    def _coerce_phase(cls, value: object) -> PhaseName:
        if isinstance(value, PhaseName):
            return value
        if isinstance(value, str):
            return PhaseName(value)
        return value  # type: ignore[return-value]


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

    @field_validator("strategy", mode="before")
    @classmethod
    def _coerce_strategy(cls, value: object) -> PhaseWorkStrategy:
        if isinstance(value, PhaseWorkStrategy):
            return value
        if isinstance(value, str):
            return PhaseWorkStrategy(value)
        return value  # type: ignore[return-value]

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


class DeterministicQaCheckConfig(BaseSchema):
    """Configuration for a single deterministic QA check."""

    check_name: str = Field(
        ..., min_length=1, description="Check identifier (e.g., 'line_length')"
    )
    enabled: bool = Field(True, description="Whether this check runs")
    severity: QaSeverity = Field(..., description="Severity for issues from this check")
    parameters: dict[str, JsonValue] | None = Field(
        None, description="Check-specific parameters"
    )

    @field_validator("severity", mode="before")
    @classmethod
    def _coerce_severity(cls, value: object) -> QaSeverity:
        if isinstance(value, QaSeverity):
            return value
        if isinstance(value, str):
            return QaSeverity(value)
        return value  # type: ignore[return-value]

    @model_validator(mode="after")
    def _validate_parameters(self) -> DeterministicQaCheckConfig:
        allowed_checks = {
            "line_length",
            "empty_translation",
            "untranslated_line",
            "whitespace",
            "unsupported_characters",
        }
        if self.check_name not in allowed_checks:
            raise ValueError(f"Unknown deterministic QA check: {self.check_name}")

        if self.check_name == "line_length":
            if self.parameters is None:
                raise ValueError("line_length check requires max_length parameter")
            max_length = self.parameters.get("max_length")
            if not isinstance(max_length, int) or max_length <= 0:
                raise ValueError("max_length must be a positive integer")
            count_mode = self.parameters.get("count_mode", "characters")
            if count_mode not in {"characters", "bytes"}:
                raise ValueError("count_mode must be 'characters' or 'bytes'")

        if self.check_name == "unsupported_characters":
            if self.parameters is None:
                raise ValueError("unsupported_characters check requires allowed_ranges")
            allowed_ranges = self.parameters.get("allowed_ranges")
            if not isinstance(allowed_ranges, list) or not allowed_ranges:
                raise ValueError("allowed_ranges must be a non-empty list")
            for entry in allowed_ranges:
                if not isinstance(entry, str):
                    raise ValueError("allowed_ranges entries must be strings")
            if "allow_common_punctuation" in self.parameters and not isinstance(
                self.parameters.get("allow_common_punctuation"), bool
            ):
                raise ValueError("allow_common_punctuation must be a boolean")

        return self


class DeterministicQaConfig(BaseSchema):
    """Configuration for the deterministic QA check suite."""

    enabled: bool = Field(True, description="Enable deterministic QA checks")
    checks: list[DeterministicQaCheckConfig] = Field(
        ..., min_length=1, description="Configured checks"
    )


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

        # No phase requirements enforced - allow flexible pipeline configurations
        # This enables per-phase testing and custom pipeline configurations

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

        llm_phases = {
            PhaseName.CONTEXT,
            PhaseName.PRETRANSLATION,
            PhaseName.TRANSLATE,
            PhaseName.QA,
            PhaseName.EDIT,
        }
        for phase in self.phases:
            if phase.phase in llm_phases:
                if phase.enabled and not phase.agents:
                    raise ValueError(
                        f"agents must be configured for {phase.phase} phase"
                    )
            elif phase.agents is not None:
                raise ValueError(f"agents are not allowed for {phase.phase} phase")
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
    logging: LoggingConfig = Field(..., description="Logging configuration")
    agents: AgentsConfig | None = Field(
        None, description="Agent discovery configuration"
    )
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

    @model_validator(mode="after")
    def validate_pipeline_parameters(self) -> RunConfig:
        """Validate pipeline parameter payloads.

        Returns:
            RunConfig: Validated run configuration.
        """
        for phase in self.pipeline.phases:
            if phase.phase != PhaseName.QA:
                continue
            if phase.parameters is None:
                continue
            deterministic = phase.parameters.get("deterministic")
            if deterministic is None:
                continue
            DeterministicQaConfig.model_validate(deterministic, strict=True)
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
