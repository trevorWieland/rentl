"""Tests for agent wiring helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import ValidationError

from rentl_agents.runtime import ProfileAgentConfig
from rentl_agents.wiring import (
    ContextSceneSummarizerAgent,
    EditBasicEditorAgent,
    PretranslationIdiomLabelerAgent,
    QaStyleGuideCriticAgent,
    TranslateDirectTranslatorAgent,
    build_agent_pools,
    create_context_agent_from_profile,
    create_edit_agent_from_profile,
    create_pretranslation_agent_from_profile,
    create_qa_agent_from_profile,
    create_translate_agent_from_profile,
    get_default_agents_dir,
    get_default_prompts_dir,
    resolve_agent_path,
)
from rentl_core.orchestrator import PhaseAgentPool
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
    PhaseExecutionConfig,
    PipelineConfig,
    ProjectConfig,
    ProjectPaths,
    RetryConfig,
    RunConfig,
)
from rentl_schemas.io import TranslatedLine
from rentl_schemas.phases import EditPhaseInput, TranslationResultLine
from rentl_schemas.primitives import (
    FileFormat,
    LogSinkType,
    PhaseName,
    PhaseWorkStrategy,
)
from rentl_schemas.version import VersionInfo


def _build_config() -> ProfileAgentConfig:
    return ProfileAgentConfig(
        api_key="test",
        base_url="http://localhost",
        model_id="gpt-5-nano",
    )


def _agent_path(base_dir: Path, *parts: str) -> Path:
    return base_dir.joinpath(*parts)


def test_wiring_creates_agents_for_profiles() -> None:
    """Wiring helpers load profiles and build agent wrappers."""
    agents_dir = get_default_agents_dir()
    prompts_dir = get_default_prompts_dir()
    config = _build_config()

    context_agent = create_context_agent_from_profile(
        profile_path=_agent_path(agents_dir, "context", "scene_summarizer.toml"),
        prompts_dir=prompts_dir,
        config=config,
    )
    pretranslation_agent = create_pretranslation_agent_from_profile(
        profile_path=_agent_path(agents_dir, "pretranslation", "idiom_labeler.toml"),
        prompts_dir=prompts_dir,
        config=config,
        chunk_size=5,
    )
    translate_agent = create_translate_agent_from_profile(
        profile_path=_agent_path(agents_dir, "translate", "direct_translator.toml"),
        prompts_dir=prompts_dir,
        config=config,
        chunk_size=5,
    )
    qa_agent = create_qa_agent_from_profile(
        profile_path=_agent_path(agents_dir, "qa", "style_guide_critic.toml"),
        prompts_dir=prompts_dir,
        config=config,
        chunk_size=5,
    )
    edit_agent = create_edit_agent_from_profile(
        profile_path=_agent_path(agents_dir, "edit", "basic_editor.toml"),
        prompts_dir=prompts_dir,
        config=config,
    )

    assert isinstance(context_agent, ContextSceneSummarizerAgent)
    assert isinstance(pretranslation_agent, PretranslationIdiomLabelerAgent)
    assert isinstance(translate_agent, TranslateDirectTranslatorAgent)
    assert isinstance(qa_agent, QaStyleGuideCriticAgent)
    assert isinstance(edit_agent, EditBasicEditorAgent)


def test_build_agent_pools_uses_execution_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent pools respect configured execution settings."""
    repo_root = Path(__file__).resolve().parents[3]
    agents_config = AgentsConfig(
        prompts_dir="packages/rentl-agents/prompts",
        agents_dir="packages/rentl-agents/agents",
    )
    project = ProjectConfig(
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        project_name="test",
        paths=ProjectPaths(
            workspace_dir=str(repo_root),
            input_path="input.txt",
            output_dir="out",
            logs_dir="logs",
        ),
        formats=FormatConfig(input_format=FileFormat.TXT, output_format=FileFormat.TXT),
        languages=LanguageConfig(source_language="ja", target_languages=["en"]),
    )
    pipeline = PipelineConfig(
        default_model=ModelSettings(model_id="gpt-4"),
        phases=[
            PhaseConfig(
                phase=PhaseName.CONTEXT,
                agents=["scene_summarizer"],
            ),
            PhaseConfig(
                phase=PhaseName.PRETRANSLATION,
                agents=["idiom_labeler"],
                execution=PhaseExecutionConfig(
                    strategy=PhaseWorkStrategy.CHUNK,
                    chunk_size=5,
                    max_parallel_agents=2,
                ),
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
    config = RunConfig(
        project=project,
        logging=LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.NOOP)]),
        agents=agents_config,
        endpoint=ModelEndpointConfig(
            provider_name="test",
            base_url="http://localhost",
            api_key_env="TEST_KEY",
        ),
        pipeline=pipeline,
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(),
        cache=CacheConfig(),
    )
    monkeypatch.setenv("TEST_KEY", "fake-key")

    pools = build_agent_pools(config=config)

    pretranslation_pool = pools.pretranslation_agents[0][1]
    assert isinstance(pretranslation_pool, PhaseAgentPool)
    assert len(pretranslation_pool._agents) == 2
    agent = pretranslation_pool._agents[0]
    assert isinstance(agent, PretranslationIdiomLabelerAgent)
    assert agent._chunk_size == 5


def test_build_agent_pools_resolves_endpoint_and_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent pools resolve endpoint refs and retry overrides."""
    repo_root = Path(__file__).resolve().parents[3]
    agents_config = AgentsConfig(
        prompts_dir="packages/rentl-agents/prompts",
        agents_dir="packages/rentl-agents/agents",
    )
    project = ProjectConfig(
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        project_name="test",
        paths=ProjectPaths(
            workspace_dir=str(repo_root),
            input_path="input.txt",
            output_dir="out",
            logs_dir="logs",
        ),
        formats=FormatConfig(input_format=FileFormat.TXT, output_format=FileFormat.TXT),
        languages=LanguageConfig(source_language="ja", target_languages=["en"]),
    )
    endpoints = EndpointSetConfig(
        default="primary",
        endpoints=[
            ModelEndpointConfig(
                provider_name="primary",
                base_url="http://localhost",
                api_key_env="PRIMARY_KEY",
            ),
            ModelEndpointConfig(
                provider_name="secondary",
                base_url="http://localhost:9999/v1",
                api_key_env="SECONDARY_KEY",
            ),
        ],
    )
    pipeline = PipelineConfig(
        default_model=ModelSettings(model_id="gpt-4", endpoint_ref="primary"),
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
                model=ModelSettings(model_id="gpt-4", endpoint_ref="secondary"),
                retry=RetryConfig(max_retries=5, backoff_s=2.0, max_backoff_s=4.0),
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
    config = RunConfig(
        project=project,
        logging=LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.NOOP)]),
        agents=agents_config,
        endpoint=None,
        endpoints=endpoints,
        pipeline=pipeline,
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(max_retries=1, backoff_s=1.0, max_backoff_s=2.0),
        cache=CacheConfig(),
    )
    monkeypatch.setenv("PRIMARY_KEY", "primary")
    monkeypatch.setenv("SECONDARY_KEY", "secondary")

    pools = build_agent_pools(config=config)
    translate_pool = pools.translate_agents[0][1]
    assert isinstance(translate_pool, PhaseAgentPool)
    translate_agent = translate_pool._agents[0]
    assert isinstance(translate_agent, TranslateDirectTranslatorAgent)
    assert translate_agent._config.base_url == "http://localhost:9999/v1"
    assert translate_agent._config.max_retries == 5
    assert translate_agent._config.retry_base_delay == 2.0
    context_pool = pools.context_agents[0][1]
    assert isinstance(context_pool, PhaseAgentPool)
    assert context_pool._max_parallel is None


def test_build_agent_pools_uses_package_defaults_when_agents_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent pools fall back to package defaults when agents config is None."""
    repo_root = Path(__file__).resolve().parents[3]
    project = ProjectConfig(
        schema_version=VersionInfo(major=0, minor=1, patch=0),
        project_name="test",
        paths=ProjectPaths(
            workspace_dir=str(repo_root),
            input_path="input.txt",
            output_dir="out",
            logs_dir="logs",
        ),
        formats=FormatConfig(input_format=FileFormat.TXT, output_format=FileFormat.TXT),
        languages=LanguageConfig(source_language="ja", target_languages=["en"]),
    )
    pipeline = PipelineConfig(
        default_model=ModelSettings(model_id="gpt-4"),
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
    config = RunConfig(
        project=project,
        logging=LoggingConfig(sinks=[LogSinkConfig(type=LogSinkType.NOOP)]),
        agents=None,
        endpoint=ModelEndpointConfig(
            provider_name="test",
            base_url="http://localhost",
            api_key_env="TEST_KEY",
        ),
        pipeline=pipeline,
        concurrency=ConcurrencyConfig(),
        retry=RetryConfig(),
        cache=CacheConfig(),
    )
    monkeypatch.setenv("TEST_KEY", "fake-key")

    pools = build_agent_pools(config=config)

    # Verify agents were created successfully from package default paths
    assert len(pools.context_agents) == 1
    assert len(pools.pretranslation_agents) == 1
    assert len(pools.translate_agents) == 1
    assert len(pools.qa_agents) == 1
    assert len(pools.edit_agents) == 1

    context_pool = pools.context_agents[0][1]
    assert isinstance(context_pool, PhaseAgentPool)
    context_agent = context_pool._agents[0]
    assert isinstance(context_agent, ContextSceneSummarizerAgent)

    pretranslation_pool = pools.pretranslation_agents[0][1]
    assert isinstance(pretranslation_pool, PhaseAgentPool)
    pretranslation_agent = pretranslation_pool._agents[0]
    assert isinstance(pretranslation_agent, PretranslationIdiomLabelerAgent)

    translate_pool = pools.translate_agents[0][1]
    assert isinstance(translate_pool, PhaseAgentPool)
    translate_agent = translate_pool._agents[0]
    assert isinstance(translate_agent, TranslateDirectTranslatorAgent)

    qa_pool = pools.qa_agents[0][1]
    assert isinstance(qa_pool, PhaseAgentPool)
    qa_agent = qa_pool._agents[0]
    assert isinstance(qa_agent, QaStyleGuideCriticAgent)

    edit_pool = pools.edit_agents[0][1]
    assert isinstance(edit_pool, PhaseAgentPool)
    edit_agent = edit_pool._agents[0]
    assert isinstance(edit_agent, EditBasicEditorAgent)


def test_profile_agent_config_requires_model_id() -> None:
    """Omitting model_id raises ValidationError."""
    with pytest.raises(ValidationError, match="model_id"):
        ProfileAgentConfig(api_key="test-key")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_agent_aggregate_validation_rejects_mismatched_lines() -> None:
    """EditBasicEditorAgent raises when output line IDs don't match input."""
    # Build a mock profile agent that returns wrong line_id
    mock_profile = AsyncMock()
    mock_profile.run = AsyncMock(
        side_effect=lambda _payload: TranslationResultLine(
            line_id="line_999", text="edited"
        )
    )
    mock_profile.update_context = lambda _ctx: None

    config = _build_config()
    agent = EditBasicEditorAgent(
        profile_agent=mock_profile,
        config=config,
        source_lang="ja",
        target_lang="en",
    )
    payload = EditPhaseInput(
        run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5f0"),
        target_language="en",
        translated_lines=[
            TranslatedLine(
                line_id="line_1",
                scene_id="scene_1",
                speaker=None,
                source_text="Hi",
                text="Hello",
                metadata=None,
                source_columns=None,
            ),
        ],
        qa_issues=None,
        reviewer_notes=None,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        pretranslation_annotations=None,
        term_candidates=None,
        glossary=None,
        style_guide=None,
    )

    # The alignment retry logic will exhaust retries and raise RuntimeError
    with pytest.raises(RuntimeError, match="line_id must match"):
        await agent.run(payload)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_agent_aggregate_validation_passes_on_matching_lines() -> None:
    """EditBasicEditorAgent succeeds when output lines match input."""
    mock_profile = AsyncMock()
    mock_profile.run = AsyncMock(
        return_value=TranslationResultLine(line_id="line_1", text="edited")
    )
    mock_profile.update_context = lambda _ctx: None

    config = _build_config()
    agent = EditBasicEditorAgent(
        profile_agent=mock_profile,
        config=config,
        source_lang="ja",
        target_lang="en",
    )
    payload = EditPhaseInput(
        run_id=UUID("01890a5c-91c8-7b2a-9f51-9b40d0cfb5f0"),
        target_language="en",
        translated_lines=[
            TranslatedLine(
                line_id="line_1",
                scene_id="scene_1",
                speaker=None,
                source_text="Hi",
                text="Hello",
                metadata=None,
                source_columns=None,
            ),
        ],
        qa_issues=None,
        reviewer_notes=None,
        scene_summaries=None,
        context_notes=None,
        project_context=None,
        pretranslation_annotations=None,
        term_candidates=None,
        glossary=None,
        style_guide=None,
    )

    result = await agent.run(payload)
    assert len(result.edited_lines) == 1
    assert result.edited_lines[0].line_id == "line_1"


class TestResolveAgentPath:
    """Tests for resolve_agent_path workspace containment."""

    def test_relative_path_resolves_within_workspace(self, tmp_path: Path) -> None:
        """Relative paths resolve against workspace_dir."""
        result = resolve_agent_path("agents/translate", tmp_path)
        assert result == (tmp_path / "agents" / "translate").resolve()

    def test_absolute_path_within_workspace_allowed(self, tmp_path: Path) -> None:
        """Absolute paths inside workspace are accepted."""
        inner = tmp_path / "agents"
        inner.mkdir()
        result = resolve_agent_path(str(inner), tmp_path)
        assert result == inner.resolve()

    def test_absolute_path_escaping_workspace_raises(self, tmp_path: Path) -> None:
        """Absolute paths outside workspace are rejected."""
        workspace = tmp_path / "project"
        workspace.mkdir()
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        with pytest.raises(ValueError, match="escapes workspace"):
            resolve_agent_path(str(outside), workspace)

    def test_relative_path_with_dotdot_escaping_raises(self, tmp_path: Path) -> None:
        """Relative paths that escape workspace via '..' are rejected."""
        workspace = tmp_path / "project"
        workspace.mkdir()
        with pytest.raises(ValueError, match="escapes workspace"):
            resolve_agent_path("../../etc/passwd", workspace)
