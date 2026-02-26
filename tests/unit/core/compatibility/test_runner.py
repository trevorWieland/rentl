"""Unit tests for the compatibility verification runner."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

from rentl_core.compatibility.loader import ModelLoadError
from rentl_core.compatibility.runner import (
    GOLDEN_SOURCE_LINE,
    PHASE_CONFIGS,
    verify_model,
    verify_registry,
)
from rentl_core.compatibility.types import (
    ModelVerificationResult,
    PhaseVerificationStatus,
    RegistryVerificationResult,
)
from rentl_schemas.compatibility import (
    VerifiedModelConfigOverrides,
    VerifiedModelEntry,
    VerifiedModelRegistry,
)
from rentl_schemas.config import ModelEndpointConfig
from rentl_schemas.primitives import PhaseName


def _build_openrouter_endpoint() -> ModelEndpointConfig:
    return ModelEndpointConfig(
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        timeout_s=120.0,
    )


def _build_local_endpoint() -> ModelEndpointConfig:
    return ModelEndpointConfig(
        provider_name="lm-studio",
        base_url="http://192.168.1.23:1234",
        api_key_env="LM_STUDIO_API_KEY",
        timeout_s=180.0,
    )


def _build_openrouter_entry() -> VerifiedModelEntry:
    return VerifiedModelEntry(
        model_id="qwen/qwen3.5-27b",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
        config_overrides=VerifiedModelConfigOverrides(
            timeout_s=120.0,
        ),
    )


def _build_local_entry() -> VerifiedModelEntry:
    return VerifiedModelEntry(
        model_id="google/gemma-3-27b",
        endpoint_type="local",
        endpoint_ref="lm-studio",
        load_endpoint=("http://192.168.1.23:1234/api/v1/models/load"),
        config_overrides=VerifiedModelConfigOverrides(
            timeout_s=180.0,
        ),
    )


@dataclass
class _FakeAgentResult:
    """Fake for pydantic-ai Agent.run() result."""

    output: str | None


async def test_verify_model_all_phases_pass() -> None:
    """All 5 phases pass when Agent.run() succeeds."""
    entry = _build_openrouter_entry()
    endpoint = _build_openrouter_endpoint()

    with (
        patch(
            "rentl_core.compatibility.runner.create_model",
        ) as mock_create,
        patch(
            "rentl_core.compatibility.runner.Agent",
        ) as mock_agent_cls,
        patch.dict(
            "os.environ",
            {"OPENROUTER_API_KEY": "test-key"},
        ),
    ):
        mock_create.return_value = (
            "fake_model",
            {"temperature": 0.2},
        )
        mock_instance = AsyncMock()
        mock_instance.run = AsyncMock(
            return_value=_FakeAgentResult(None),
        )
        mock_agent_cls.return_value = mock_instance

        result = await verify_model(
            entry=entry,
            endpoint=endpoint,
        )

    assert isinstance(result, ModelVerificationResult)
    assert result.passed is True
    assert result.model_id == "qwen/qwen3.5-27b"
    assert len(result.phase_results) == 5
    for pr in result.phase_results:
        assert pr.status == PhaseVerificationStatus.PASSED
        assert pr.error_message is None


async def test_verify_model_phase_failure() -> None:
    """Phase failure captured with error details."""
    entry = _build_openrouter_entry()
    endpoint = _build_openrouter_endpoint()

    call_count = 0

    def _side_effect(
        *args: object,
        **kwargs: object,
    ) -> _FakeAgentResult:
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            raise RuntimeError("output validation failed")
        return _FakeAgentResult(None)

    with (
        patch(
            "rentl_core.compatibility.runner.create_model",
        ) as mock_create,
        patch(
            "rentl_core.compatibility.runner.Agent",
        ) as mock_agent_cls,
        patch.dict(
            "os.environ",
            {"OPENROUTER_API_KEY": "test-key"},
        ),
    ):
        mock_create.return_value = (
            "fake_model",
            {"temperature": 0.2},
        )
        mock_instance = AsyncMock()
        mock_instance.run = AsyncMock(
            side_effect=_side_effect,
        )
        mock_agent_cls.return_value = mock_instance

        result = await verify_model(
            entry=entry,
            endpoint=endpoint,
        )

    assert result.passed is False
    ctx = result.phase_results[0]
    pre = result.phase_results[1]
    trl = result.phase_results[2]
    assert ctx.status == PhaseVerificationStatus.PASSED
    assert pre.status == PhaseVerificationStatus.PASSED
    assert trl.status == PhaseVerificationStatus.FAILED
    assert "output validation failed" in (trl.error_message or "")
    qa = result.phase_results[3]
    edit = result.phase_results[4]
    assert qa.status == PhaseVerificationStatus.PASSED
    assert edit.status == PhaseVerificationStatus.PASSED


async def test_verify_model_local_loads_first() -> None:
    """Local models call LM Studio load API first."""
    entry = _build_local_entry()
    endpoint = _build_local_endpoint()

    with (
        patch(
            "rentl_core.compatibility.runner.create_model",
        ) as mock_create,
        patch(
            "rentl_core.compatibility.runner.Agent",
        ) as mock_agent_cls,
        patch(
            "rentl_core.compatibility.runner.load_lm_studio_model",
        ) as mock_load,
        patch.dict(
            "os.environ",
            {"LM_STUDIO_API_KEY": "test-key"},
        ),
    ):
        mock_create.return_value = (
            "fake_model",
            {"temperature": 0.2},
        )
        mock_instance = AsyncMock()
        mock_instance.run = AsyncMock(
            return_value=_FakeAgentResult(None),
        )
        mock_agent_cls.return_value = mock_instance

        result = await verify_model(
            entry=entry,
            endpoint=endpoint,
        )

    assert result.passed is True
    mock_load.assert_awaited_once_with(
        load_endpoint=("http://192.168.1.23:1234/api/v1/models/load"),
        model_id="google/gemma-3-27b",
        timeout_s=180.0,
    )


async def test_verify_model_local_load_failure() -> None:
    """Model load failure skips all phases."""
    entry = _build_local_entry()
    endpoint = _build_local_endpoint()

    with (
        patch(
            "rentl_core.compatibility.runner.load_lm_studio_model",
            side_effect=ModelLoadError("refused"),
        ),
        patch.dict(
            "os.environ",
            {"LM_STUDIO_API_KEY": "test-key"},
        ),
    ):
        result = await verify_model(
            entry=entry,
            endpoint=endpoint,
        )

    assert result.passed is False
    assert len(result.phase_results) == 1
    assert "Model loading failed" in (result.phase_results[0].error_message or "")


async def test_verify_registry_filter_endpoint() -> None:
    """Registry filters entries by endpoint type."""
    registry = VerifiedModelRegistry(
        models=[
            _build_openrouter_entry(),
            _build_local_entry(),
        ],
    )
    endpoints = {
        "openrouter": _build_openrouter_endpoint(),
        "lm-studio": _build_local_endpoint(),
    }

    with (
        patch(
            "rentl_core.compatibility.runner.create_model",
        ) as mock_create,
        patch(
            "rentl_core.compatibility.runner.Agent",
        ) as mock_agent_cls,
        patch.dict(
            "os.environ",
            {"OPENROUTER_API_KEY": "test-key"},
        ),
    ):
        mock_create.return_value = (
            "fake_model",
            {"temperature": 0.2},
        )
        mock_instance = AsyncMock()
        mock_instance.run = AsyncMock(
            return_value=_FakeAgentResult(None),
        )
        mock_agent_cls.return_value = mock_instance

        result = await verify_registry(
            registry=registry,
            endpoints=endpoints,
            endpoint_filter="openrouter",
        )

    assert isinstance(result, RegistryVerificationResult)
    assert len(result.model_results) == 1
    assert result.model_results[0].model_id == "qwen/qwen3.5-27b"


async def test_verify_registry_filter_model() -> None:
    """Registry filters entries by model ID."""
    registry = VerifiedModelRegistry(
        models=[
            _build_openrouter_entry(),
            _build_local_entry(),
        ],
    )
    endpoints = {
        "openrouter": _build_openrouter_endpoint(),
        "lm-studio": _build_local_endpoint(),
    }

    with (
        patch(
            "rentl_core.compatibility.runner.create_model",
        ) as mock_create,
        patch(
            "rentl_core.compatibility.runner.Agent",
        ) as mock_agent_cls,
        patch(
            "rentl_core.compatibility.runner.load_lm_studio_model",
        ),
        patch.dict(
            "os.environ",
            {"LM_STUDIO_API_KEY": "test-key"},
        ),
    ):
        mock_create.return_value = (
            "fake_model",
            {"temperature": 0.2},
        )
        mock_instance = AsyncMock()
        mock_instance.run = AsyncMock(
            return_value=_FakeAgentResult(None),
        )
        mock_agent_cls.return_value = mock_instance

        result = await verify_registry(
            registry=registry,
            endpoints=endpoints,
            model_filter="google/gemma-3-27b",
        )

    assert len(result.model_results) == 1
    assert result.model_results[0].model_id == "google/gemma-3-27b"


async def test_verify_registry_missing_endpoint() -> None:
    """Missing endpoint_ref produces a failure result."""
    registry = VerifiedModelRegistry(
        models=[_build_openrouter_entry()],
    )

    result = await verify_registry(
        registry=registry,
        endpoints={},
    )

    assert result.passed is False
    assert len(result.model_results) == 1
    assert result.model_results[0].passed is False
    assert "No endpoint configured" in (
        result.model_results[0].phase_results[0].error_message or ""
    )


def test_golden_source_line_is_valid() -> None:
    """The golden source line is a valid SourceLine."""
    assert GOLDEN_SOURCE_LINE.line_id == "scene_001_0001"
    assert len(GOLDEN_SOURCE_LINE.text) > 0


def test_phase_configs_cover_all_phases() -> None:
    """Phase configs include all 5 LLM pipeline phases."""
    phases = [phase for phase, _, _, _ in PHASE_CONFIGS]
    assert phases == [
        PhaseName.CONTEXT,
        PhaseName.PRETRANSLATION,
        PhaseName.TRANSLATE,
        PhaseName.QA,
        PhaseName.EDIT,
    ]
