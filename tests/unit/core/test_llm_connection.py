"""Unit tests for LLM connection planning and validation."""

from __future__ import annotations

from rentl_core.llm.connection import build_connection_plan, validate_connections
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
    PhaseConfig,
    PipelineConfig,
    ProjectConfig,
    ProjectPaths,
    RetryConfig,
    RunConfig,
)
from rentl_schemas.llm import (
    LlmConnectionStatus,
    LlmEndpointTarget,
    LlmPromptRequest,
    LlmPromptResponse,
)
from rentl_schemas.primitives import FileFormat, LogSinkType, PhaseName
from rentl_schemas.version import VersionInfo


class _FakeRuntime:
    async def run_prompt(
        self, request: LlmPromptRequest, *, api_key: str
    ) -> LlmPromptResponse:
        return LlmPromptResponse(
            model_id=request.runtime.model.model_id,
            output_text="ok",
        )


def test_build_connection_plan_dedupes_and_tracks_unused() -> None:
    """Ensure connection plan resolves endpoints and unused entries."""
    config = _build_config()

    targets, unused = build_connection_plan(config)

    assert {target.runtime.endpoint.provider_name for target in targets} == {
        "primary",
        "secondary",
    }
    primary = next(
        target
        for target in targets
        if target.runtime.endpoint.provider_name == "primary"
    )
    assert set(primary.phases) == {
        PhaseName.CONTEXT,
        PhaseName.PRETRANSLATION,
        PhaseName.QA,
        PhaseName.EDIT,
    }
    assert [endpoint.provider_name for endpoint in unused] == ["tertiary"]


async def test_validate_connections_returns_report() -> None:
    """Ensure connectivity checks return a summarized report."""
    config = _build_config()
    targets, unused = build_connection_plan(config)
    runtime = _FakeRuntime()

    def lookup(_: LlmEndpointTarget) -> str | None:
        return "fake-key"

    report = await validate_connections(
        runtime,
        targets,
        prompt="Hello",
        system_prompt=None,
        api_key_lookup=lookup,
        skipped_endpoints=unused,
    )

    assert report.success_count == 2
    assert report.failure_count == 0
    assert report.skipped_count == 1
    statuses = {result.status for result in report.results}
    assert LlmConnectionStatus.SUCCESS in statuses
    assert LlmConnectionStatus.SKIPPED in statuses


def _build_config() -> RunConfig:
    return RunConfig(
        project=_base_project_config(),
        logging=_logging_config(),
        agents=_agents_config(),
        endpoint=None,
        endpoints=_endpoints_config(),
        pipeline=_pipeline_config(),
        concurrency=ConcurrencyConfig(
            max_parallel_requests=1,
            max_parallel_scenes=1,
        ),
        retry=RetryConfig(
            max_retries=1,
            backoff_s=1.0,
            max_backoff_s=2.0,
        ),
        cache=CacheConfig(
            enabled=False,
            cache_dir=None,
            ttl_s=None,
            max_entries=None,
        ),
    )


def _logging_config() -> LoggingConfig:
    return LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.NOOP)])


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


def _pipeline_config() -> PipelineConfig:
    default_model = _model_settings("gpt-4", "primary")
    return PipelineConfig(
        default_model=default_model,
        phases=[
            PhaseConfig(
                phase=PhaseName.CONTEXT,
                enabled=True,
                agents=["scene_summarizer"],
                model=None,
                concurrency=None,
                retry=None,
                execution=None,
                parameters=None,
            ),
            PhaseConfig(
                phase=PhaseName.PRETRANSLATION,
                enabled=True,
                agents=["idiom_labeler"],
                model=None,
                concurrency=None,
                retry=None,
                execution=None,
                parameters=None,
            ),
            PhaseConfig(
                phase=PhaseName.TRANSLATE,
                enabled=True,
                agents=["direct_translator"],
                model=_model_settings("gpt-4", "secondary"),
                concurrency=None,
                retry=None,
                execution=None,
                parameters=None,
            ),
            PhaseConfig(
                phase=PhaseName.QA,
                enabled=True,
                agents=["style_guide_critic"],
                model=None,
                concurrency=None,
                retry=None,
                execution=None,
                parameters=None,
            ),
            PhaseConfig(
                phase=PhaseName.EDIT,
                enabled=True,
                agents=["basic_editor"],
                model=None,
                concurrency=None,
                retry=None,
                execution=None,
                parameters=None,
            ),
        ],
    )


def _agents_config() -> AgentsConfig:
    return AgentsConfig(
        prompts_dir="/tmp/prompts",
        agents_dir="/tmp/agents",
    )


def _endpoints_config() -> EndpointSetConfig:
    return EndpointSetConfig(
        default="primary",
        endpoints=[
            ModelEndpointConfig(
                provider_name="primary",
                base_url="http://localhost:8001/v1",
                api_key_env="PRIMARY_KEY",
                timeout_s=30.0,
            ),
            ModelEndpointConfig(
                provider_name="secondary",
                base_url="http://localhost:8002/v1",
                api_key_env="SECONDARY_KEY",
                timeout_s=30.0,
            ),
            ModelEndpointConfig(
                provider_name="tertiary",
                base_url="http://localhost:8003/v1",
                api_key_env="TERTIARY_KEY",
                timeout_s=30.0,
            ),
        ],
    )


def _model_settings(model_id: str, endpoint_ref: str) -> ModelSettings:
    return ModelSettings(
        model_id=model_id,
        endpoint_ref=endpoint_ref,
        temperature=0.2,
        max_output_tokens=128,
        top_p=1.0,
        presence_penalty=0.0,
        frequency_penalty=0.0,
    )
