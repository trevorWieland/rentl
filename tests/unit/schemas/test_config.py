"""Unit tests for configuration schema validation."""

import pytest
from pydantic import ValidationError

from rentl_schemas.config import (
    AgentsConfig,
    CacheConfig,
    ConcurrencyConfig,
    EndpointSetConfig,
    FormatConfig,
    LanguageConfig,
    LoggingConfig,
    LogSinkConfig,
    ModelEndpointConfig,
    ModelSettings,
    OpenRouterProviderRoutingConfig,
    PhaseConfig,
    PhaseExecutionConfig,
    PipelineConfig,
    ProjectConfig,
    ProjectPaths,
    RetryConfig,
    RunConfig,
)
from rentl_schemas.primitives import (
    FileFormat,
    LogSinkType,
    PhaseName,
    PhaseWorkStrategy,
)
from rentl_schemas.version import VersionInfo


def test_language_config_rejects_duplicate_targets() -> None:
    """Ensure duplicate target languages are rejected."""
    with pytest.raises(ValidationError):
        LanguageConfig(
            source_language="en",
            target_languages=["ja", "ja"],
        )


def test_language_config_rejects_source_in_targets() -> None:
    """Ensure source language cannot appear in target list."""
    with pytest.raises(ValidationError):
        LanguageConfig(
            source_language="en",
            target_languages=["en", "ja"],
        )


def test_pipeline_config_enforces_phase_order() -> None:
    """Ensure phases follow canonical order."""
    with pytest.raises(ValidationError):
        PipelineConfig(
            default_model=ModelSettings(model_id="gpt-4"),
            phases=[
                PhaseConfig(
                    phase=PhaseName.TRANSLATE,
                    agents=["direct_translator"],
                ),
                PhaseConfig(
                    phase=PhaseName.CONTEXT,
                    agents=["scene_summarizer"],
                ),
                PhaseConfig(
                    phase=PhaseName.PRETRANSLATION,
                    agents=["idiom_labeler"],
                ),
                PhaseConfig(
                    phase=PhaseName.QA,
                    agents=["style_guide_critic"],
                ),
                PhaseConfig(
                    phase=PhaseName.EDIT,
                    agents=["basic_editor"],
                ),
            ],
        )


def test_pipeline_config_requires_default_model() -> None:
    """Ensure default_model is required when phases omit model settings."""
    with pytest.raises(ValidationError):
        PipelineConfig(
            default_model=None,
            phases=[
                PhaseConfig(
                    phase=PhaseName.CONTEXT,
                    agents=["scene_summarizer"],
                ),
                PhaseConfig(
                    phase=PhaseName.PRETRANSLATION,
                    agents=["idiom_labeler"],
                ),
                PhaseConfig(
                    phase=PhaseName.TRANSLATE,
                    agents=["direct_translator"],
                ),
                PhaseConfig(
                    phase=PhaseName.QA,
                    agents=["style_guide_critic"],
                ),
                PhaseConfig(
                    phase=PhaseName.EDIT,
                    agents=["basic_editor"],
                ),
            ],
        )


def test_phase_execution_requires_chunk_size() -> None:
    """Ensure chunk strategy requires chunk_size."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(strategy=PhaseWorkStrategy.CHUNK)


def test_phase_execution_rejects_full_with_chunk_size() -> None:
    """Ensure chunk_size is rejected for full strategy."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(
            strategy=PhaseWorkStrategy.FULL,
            chunk_size=10,
        )


def test_format_config_coerces_string_values() -> None:
    """Ensure format strings are coerced to enums."""
    config = FormatConfig.model_validate({
        "input_format": "txt",
        "output_format": "jsonl",
    })

    assert config.input_format == FileFormat.TXT
    assert config.output_format == FileFormat.JSONL


def test_log_sink_config_coerces_string_values() -> None:
    """Ensure log sink strings are coerced to enums."""
    config = LogSinkConfig.model_validate({"type": "file"})

    assert config.type == LogSinkType.FILE


def test_phase_config_coerces_string_values() -> None:
    """Ensure phase strings are coerced to enums."""
    config = PhaseConfig.model_validate({"phase": "ingest"})

    assert config.phase == PhaseName.INGEST


def test_phase_execution_config_coerces_string_values() -> None:
    """Ensure strategy strings are coerced to enums."""
    config = PhaseExecutionConfig.model_validate({
        "strategy": "scene",
        "scene_batch_size": 1,
    })

    assert config.strategy == PhaseWorkStrategy.SCENE


def test_model_settings_coerces_reasoning_effort() -> None:
    """Ensure reasoning effort strings are coerced to enums."""
    config = ModelSettings.model_validate({
        "model_id": "gpt-4",
        "reasoning_effort": "medium",
    })

    assert config.reasoning_effort is not None
    assert config.reasoning_effort == "medium"


def _base_run_config(phases: list[PhaseConfig]) -> RunConfig:
    return RunConfig(
        project=ProjectConfig(
            schema_version=VersionInfo(major=0, minor=1, patch=0),
            project_name="test",
            paths=ProjectPaths(
                workspace_dir="/tmp",
                input_path="input.txt",
                output_dir="out",
                logs_dir="logs",
            ),
            formats=FormatConfig(
                input_format=FileFormat.TXT,
                output_format=FileFormat.TXT,
            ),
            languages=LanguageConfig(
                source_language="en",
                target_languages=["ja"],
            ),
        ),
        logging=LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.FILE)]),
        agents=AgentsConfig(prompts_dir="/tmp/prompts", agents_dir="/tmp/agents"),
        endpoint=ModelEndpointConfig(
            provider_name="test",
            base_url="http://localhost",
            api_key_env="TEST_KEY",
        ),
        endpoints=None,
        pipeline=PipelineConfig(
            default_model=ModelSettings(model_id="gpt-4"),
            phases=phases,
        ),
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(),
        cache=CacheConfig(),
    )


def test_deterministic_check_requires_line_length_params() -> None:
    """Ensure line_length requires max_length."""
    with pytest.raises(ValidationError):
        _base_run_config(
            phases=[
                PhaseConfig(phase=PhaseName.INGEST),
                PhaseConfig(phase=PhaseName.CONTEXT, agents=["scene_summarizer"]),
                PhaseConfig(phase=PhaseName.PRETRANSLATION, agents=["idiom_labeler"]),
                PhaseConfig(phase=PhaseName.TRANSLATE, agents=["direct_translator"]),
                PhaseConfig(
                    phase=PhaseName.QA,
                    agents=["style_guide_critic"],
                    parameters={
                        "deterministic": {
                            "enabled": True,
                            "checks": [
                                {
                                    "check_name": "line_length",
                                    "enabled": True,
                                    "severity": "minor",
                                }
                            ],
                        }
                    },
                ),
                PhaseConfig(phase=PhaseName.EDIT, agents=["basic_editor"]),
            ]
        )


def test_deterministic_check_validates_allowed_ranges() -> None:
    """Ensure unsupported_characters validates allowed_ranges."""
    with pytest.raises(ValidationError):
        _base_run_config(
            phases=[
                PhaseConfig(phase=PhaseName.INGEST),
                PhaseConfig(phase=PhaseName.CONTEXT, agents=["scene_summarizer"]),
                PhaseConfig(phase=PhaseName.PRETRANSLATION, agents=["idiom_labeler"]),
                PhaseConfig(phase=PhaseName.TRANSLATE, agents=["direct_translator"]),
                PhaseConfig(
                    phase=PhaseName.QA,
                    agents=["style_guide_critic"],
                    parameters={
                        "deterministic": {
                            "enabled": True,
                            "checks": [
                                {
                                    "check_name": "unsupported_characters",
                                    "enabled": True,
                                    "severity": "minor",
                                    "parameters": {"allowed_ranges": []},
                                }
                            ],
                        }
                    },
                ),
                PhaseConfig(phase=PhaseName.EDIT, agents=["basic_editor"]),
            ]
        )


def test_phase_execution_rejects_scene_with_chunk_size() -> None:
    """Ensure chunk_size is rejected for scene strategy."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(
            strategy=PhaseWorkStrategy.SCENE,
            chunk_size=10,
        )


def test_phase_execution_rejects_chunk_with_scene_batch_size() -> None:
    """Ensure scene_batch_size is rejected for chunk strategy."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(
            strategy=PhaseWorkStrategy.CHUNK,
            chunk_size=10,
            scene_batch_size=2,
        )


def test_logging_config_rejects_duplicate_sink_types() -> None:
    """Ensure logging config rejects duplicate sink types."""
    with pytest.raises(ValidationError):
        LoggingConfig(
            sinks=[
                LogSinkConfig(type=LogSinkType.FILE),
                LogSinkConfig(type=LogSinkType.FILE),
            ]
        )


def test_phase_execution_rejects_full_with_route_batch_size() -> None:
    """Ensure route_batch_size is rejected for full strategy."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(
            strategy=PhaseWorkStrategy.FULL,
            route_batch_size=2,
        )


def test_phase_execution_rejects_route_with_chunk_size() -> None:
    """Ensure chunk_size is rejected for route strategy."""
    with pytest.raises(ValidationError):
        PhaseExecutionConfig(
            strategy=PhaseWorkStrategy.ROUTE,
            chunk_size=10,
        )


def test_phase_execution_allows_route_with_route_batch_size() -> None:
    """Ensure route strategy accepts route_batch_size."""
    execution = PhaseExecutionConfig(
        strategy=PhaseWorkStrategy.ROUTE,
        route_batch_size=3,
    )
    assert execution.route_batch_size == 3


def test_model_endpoint_config_rejects_missing_scheme() -> None:
    """Ensure base_url requires http/https scheme."""
    with pytest.raises(ValidationError):
        ModelEndpointConfig(
            provider_name="local",
            base_url="localhost:8002/api/v1",
            api_key_env="TEST_KEY",
        )


def test_model_endpoint_config_accepts_http_url() -> None:
    """Ensure http base_url values are accepted."""
    endpoint = ModelEndpointConfig(
        provider_name="local",
        base_url="http://localhost:8002/api/v1",
        api_key_env="TEST_KEY",
    )
    assert endpoint.base_url == "http://localhost:8002/api/v1"


def test_model_endpoint_config_defaults_openrouter_provider() -> None:
    """Ensure OpenRouter endpoints default require_parameters to true."""
    endpoint = ModelEndpointConfig(
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_KEY",
    )
    assert endpoint.openrouter_provider is not None
    assert endpoint.openrouter_provider.require_parameters is True


def test_model_endpoint_config_rejects_openrouter_provider_on_non_openrouter() -> None:
    """Ensure OpenRouter routing config is rejected for non-OpenRouter endpoints."""
    with pytest.raises(ValidationError):
        ModelEndpointConfig(
            provider_name="local",
            base_url="http://localhost:8002/v1",
            api_key_env="LOCAL_KEY",
            openrouter_provider=OpenRouterProviderRoutingConfig(
                require_parameters=True
            ),
        )


def test_model_endpoint_config_rejects_openrouter_require_parameters_false() -> None:
    """Ensure OpenRouter endpoints cannot disable required-parameter routing."""
    with pytest.raises(ValidationError):
        ModelEndpointConfig(
            provider_name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="OPENROUTER_KEY",
            openrouter_provider=OpenRouterProviderRoutingConfig(
                require_parameters=False
            ),
        )


def test_model_endpoint_config_appends_v1_for_root_url() -> None:
    """Ensure root URLs are normalized to include /v1."""
    endpoint = ModelEndpointConfig(
        provider_name="local",
        base_url="http://localhost:8002",
        api_key_env="TEST_KEY",
    )
    assert endpoint.base_url == "http://localhost:8002/v1"


def test_endpoint_set_requires_unique_provider_names() -> None:
    """Ensure endpoint provider_name values are unique."""
    endpoint = ModelEndpointConfig(
        provider_name="primary",
        base_url="http://localhost:8002/api/v1",
        api_key_env="PRIMARY_KEY",
    )
    with pytest.raises(ValidationError):
        EndpointSetConfig(
            default="primary",
            endpoints=[endpoint, endpoint],
        )


def test_endpoint_set_requires_default_match() -> None:
    """Ensure default endpoint reference exists in endpoints list."""
    endpoint = ModelEndpointConfig(
        provider_name="primary",
        base_url="http://localhost:8002/api/v1",
        api_key_env="PRIMARY_KEY",
    )
    with pytest.raises(ValidationError):
        EndpointSetConfig(default="missing", endpoints=[endpoint])


def test_run_config_rejects_endpoint_ref_without_endpoints() -> None:
    """Ensure endpoint_ref requires endpoints config."""
    pipeline = _base_pipeline_config(
        ModelSettings(model_id="gpt-4", endpoint_ref="primary")
    )
    with pytest.raises(ValidationError):
        RunConfig(
            project=_base_project_config(),
            logging=_base_logging_config(),
            agents=_base_agents_config(),
            endpoint=ModelEndpointConfig(
                provider_name="legacy",
                base_url="http://localhost:8002/api/v1",
                api_key_env="LEGACY_KEY",
            ),
            endpoints=None,
            pipeline=pipeline,
            concurrency=ConcurrencyConfig(),
            retry=RetryConfig(),
            cache=CacheConfig(),
        )


def test_run_config_rejects_both_endpoint_modes() -> None:
    """Ensure endpoint and endpoints are mutually exclusive."""
    endpoints = EndpointSetConfig(
        default="primary",
        endpoints=[
            ModelEndpointConfig(
                provider_name="primary",
                base_url="http://localhost:8002/api/v1",
                api_key_env="PRIMARY_KEY",
            )
        ],
    )
    pipeline = _base_pipeline_config(ModelSettings(model_id="gpt-4"))
    with pytest.raises(ValidationError):
        RunConfig(
            project=_base_project_config(),
            logging=_base_logging_config(),
            agents=_base_agents_config(),
            endpoint=ModelEndpointConfig(
                provider_name="legacy",
                base_url="http://localhost:8002/api/v1",
                api_key_env="LEGACY_KEY",
            ),
            endpoints=endpoints,
            pipeline=pipeline,
            concurrency=ConcurrencyConfig(),
            retry=RetryConfig(),
            cache=CacheConfig(),
        )


def test_run_config_rejects_unknown_endpoint_ref() -> None:
    """Ensure endpoint_ref must exist in configured endpoints."""
    endpoints = EndpointSetConfig(
        default="primary",
        endpoints=[
            ModelEndpointConfig(
                provider_name="primary",
                base_url="http://localhost:8002/api/v1",
                api_key_env="PRIMARY_KEY",
            )
        ],
    )
    pipeline = _base_pipeline_config(
        ModelSettings(model_id="gpt-4", endpoint_ref="missing")
    )
    with pytest.raises(ValidationError):
        RunConfig(
            project=_base_project_config(),
            logging=_base_logging_config(),
            agents=_base_agents_config(),
            endpoint=None,
            endpoints=endpoints,
            pipeline=pipeline,
            concurrency=ConcurrencyConfig(),
            retry=RetryConfig(),
            cache=CacheConfig(),
        )


def test_run_config_accepts_multi_endpoints() -> None:
    """Ensure valid endpoint_ref passes with endpoints config."""
    endpoints = EndpointSetConfig(
        default="primary",
        endpoints=[
            ModelEndpointConfig(
                provider_name="primary",
                base_url="http://localhost:8002/api/v1",
                api_key_env="PRIMARY_KEY",
            )
        ],
    )
    pipeline = _base_pipeline_config(
        ModelSettings(model_id="gpt-4", endpoint_ref="primary")
    )
    config = RunConfig(
        project=_base_project_config(),
        logging=_base_logging_config(),
        agents=_base_agents_config(),
        endpoint=None,
        endpoints=endpoints,
        pipeline=pipeline,
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(),
        cache=CacheConfig(),
    )
    assert config.resolve_endpoint_ref(model=pipeline.default_model) == "primary"


def _base_project_config() -> ProjectConfig:
    return ProjectConfig(
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        project_name="test-project",
        paths=ProjectPaths(
            workspace_dir="/tmp",
            input_path="/tmp/input.txt",
            output_dir="/tmp/output",
            logs_dir="/tmp/logs",
        ),
        formats=FormatConfig(input_format=FileFormat.TXT, output_format=FileFormat.TXT),
        languages=LanguageConfig(source_language="en", target_languages=["ja"]),
    )


def _base_logging_config() -> LoggingConfig:
    return LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.FILE)])


def _base_agents_config() -> AgentsConfig:
    return AgentsConfig(
        prompts_dir="/tmp/prompts",
        agents_dir="/tmp/agents",
    )


def _base_pipeline_config(default_model: ModelSettings) -> PipelineConfig:
    return PipelineConfig(
        default_model=default_model,
        phases=[
            PhaseConfig(
                phase=PhaseName.CONTEXT,
                agents=["scene_summarizer"],
            ),
            PhaseConfig(
                phase=PhaseName.PRETRANSLATION,
                agents=["idiom_labeler"],
            ),
            PhaseConfig(
                phase=PhaseName.TRANSLATE,
                agents=["direct_translator"],
            ),
            PhaseConfig(
                phase=PhaseName.QA,
                agents=["style_guide_critic"],
            ),
            PhaseConfig(
                phase=PhaseName.EDIT,
                agents=["basic_editor"],
            ),
        ],
    )


def test_run_config_accepts_none_agents_config() -> None:
    """Ensure agents config can be omitted (defaults to package agents)."""
    config = RunConfig(
        project=_base_project_config(),
        logging=_base_logging_config(),
        agents=None,
        endpoint=ModelEndpointConfig(
            provider_name="test",
            base_url="http://localhost:8002/api/v1",
            api_key_env="TEST_KEY",
        ),
        endpoints=None,
        pipeline=_base_pipeline_config(ModelSettings(model_id="gpt-4")),
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(),
        cache=CacheConfig(),
    )
    assert config.agents is None


def test_run_config_rejects_invalid_openrouter_model_id_legacy() -> None:
    """Ensure invalid OpenRouter model IDs are rejected with legacy endpoint."""
    pipeline = _base_pipeline_config(ModelSettings(model_id="no-slash"))
    with pytest.raises(ValidationError, match="Invalid OpenRouter model ID"):
        RunConfig(
            project=_base_project_config(),
            logging=_base_logging_config(),
            agents=_base_agents_config(),
            endpoint=ModelEndpointConfig(
                provider_name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_KEY",
            ),
            endpoints=None,
            pipeline=pipeline,
            concurrency=ConcurrencyConfig(),
            retry=RetryConfig(),
            cache=CacheConfig(),
        )


def test_run_config_accepts_valid_openrouter_model_id_legacy() -> None:
    """Ensure valid OpenRouter model IDs pass with legacy endpoint."""
    pipeline = _base_pipeline_config(ModelSettings(model_id="openai/gpt-4o"))
    config = RunConfig(
        project=_base_project_config(),
        logging=_base_logging_config(),
        agents=_base_agents_config(),
        endpoint=ModelEndpointConfig(
            provider_name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="OPENROUTER_KEY",
        ),
        endpoints=None,
        pipeline=pipeline,
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(),
        cache=CacheConfig(),
    )
    assert config.pipeline.default_model is not None
    assert config.pipeline.default_model.model_id == "openai/gpt-4o"


def test_run_config_rejects_invalid_openrouter_model_id_multi() -> None:
    """Ensure invalid OpenRouter model IDs rejected with multi-endpoint config."""
    endpoints = EndpointSetConfig(
        default="openrouter",
        endpoints=[
            ModelEndpointConfig(
                provider_name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_KEY",
            ),
        ],
    )
    pipeline = _base_pipeline_config(ModelSettings(model_id="bad-model-id"))
    with pytest.raises(ValidationError, match="Invalid OpenRouter model ID"):
        RunConfig(
            project=_base_project_config(),
            logging=_base_logging_config(),
            agents=_base_agents_config(),
            endpoint=None,
            endpoints=endpoints,
            pipeline=pipeline,
            concurrency=ConcurrencyConfig(),
            retry=RetryConfig(),
            cache=CacheConfig(),
        )


def test_run_config_skips_validation_for_non_openrouter_endpoint() -> None:
    """Ensure non-OpenRouter endpoints don't require provider/model format."""
    pipeline = _base_pipeline_config(ModelSettings(model_id="local-model"))
    config = RunConfig(
        project=_base_project_config(),
        logging=_base_logging_config(),
        agents=_base_agents_config(),
        endpoint=ModelEndpointConfig(
            provider_name="local",
            base_url="http://localhost:8002/api/v1",
            api_key_env="LOCAL_KEY",
        ),
        endpoints=None,
        pipeline=pipeline,
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(),
        cache=CacheConfig(),
    )
    assert config.pipeline.default_model is not None
    assert config.pipeline.default_model.model_id == "local-model"
