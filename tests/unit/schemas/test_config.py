"""Unit tests for configuration schema validation."""

import pytest
from pydantic import ValidationError

from rentl_schemas.config import (
    CacheConfig,
    ConcurrencyConfig,
    EndpointSetConfig,
    FormatConfig,
    LanguageConfig,
    ModelEndpointConfig,
    ModelSettings,
    PhaseConfig,
    PhaseExecutionConfig,
    PipelineConfig,
    ProjectConfig,
    ProjectPaths,
    RetryConfig,
    RunConfig,
)
from rentl_schemas.primitives import FileFormat, PhaseName, PhaseWorkStrategy
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
                PhaseConfig(phase=PhaseName.TRANSLATE),
                PhaseConfig(phase=PhaseName.CONTEXT),
                PhaseConfig(phase=PhaseName.PRETRANSLATION),
                PhaseConfig(phase=PhaseName.QA),
                PhaseConfig(phase=PhaseName.EDIT),
            ],
        )


def test_pipeline_config_requires_default_model() -> None:
    """Ensure default_model is required when phases omit model settings."""
    with pytest.raises(ValidationError):
        PipelineConfig(
            default_model=None,
            phases=[
                PhaseConfig(phase=PhaseName.CONTEXT),
                PhaseConfig(phase=PhaseName.PRETRANSLATION),
                PhaseConfig(phase=PhaseName.TRANSLATE),
                PhaseConfig(phase=PhaseName.QA),
                PhaseConfig(phase=PhaseName.EDIT),
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


def _base_pipeline_config(default_model: ModelSettings) -> PipelineConfig:
    return PipelineConfig(
        default_model=default_model,
        phases=[
            PhaseConfig(phase=PhaseName.CONTEXT),
            PhaseConfig(phase=PhaseName.PRETRANSLATION),
            PhaseConfig(phase=PhaseName.TRANSLATE),
            PhaseConfig(phase=PhaseName.QA),
            PhaseConfig(phase=PhaseName.EDIT),
        ],
    )
