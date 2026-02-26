"""Unit tests for the compatibility verification runner."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest

from rentl_core.compatibility.loader import ModelLoadError, ModelUnloadError
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
            timeout_s=5.0,
            load_timeout_s=120.0,
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
        *args: str,
        **kwargs: str | int | float | bool | None,
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
    # Fail-fast: remaining phases are skipped after first failure
    qa = result.phase_results[3]
    edit = result.phase_results[4]
    assert qa.status == PhaseVerificationStatus.SKIPPED
    assert edit.status == PhaseVerificationStatus.SKIPPED


async def test_verify_model_fail_fast_skips_remaining_phases() -> None:
    """Phases after the first failure are skipped, not executed."""
    entry = _build_openrouter_entry()
    endpoint = _build_openrouter_endpoint()

    call_count = 0

    def _side_effect(
        *args: str,
        **kwargs: str | int | float | bool | None,
    ) -> _FakeAgentResult:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("context phase failed")
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
    assert len(result.phase_results) == 5
    # First phase failed
    assert result.phase_results[0].status == PhaseVerificationStatus.FAILED
    assert "context phase failed" in (result.phase_results[0].error_message or "")
    # Remaining 4 phases are skipped, not executed
    for pr in result.phase_results[1:]:
        assert pr.status == PhaseVerificationStatus.SKIPPED
    # Agent.run() was only called once (only the first phase)
    assert mock_instance.run.await_count == 1


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
        patch(
            "rentl_core.compatibility.runner.unload_lm_studio_model",
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

        result = await verify_model(
            entry=entry,
            endpoint=endpoint,
        )

    assert result.passed is True
    mock_load.assert_awaited_once_with(
        load_endpoint=("http://192.168.1.23:1234/api/v1/models/load"),
        model_id="google/gemma-3-27b",
        api_key="test-key",
        timeout_s=120.0,
    )


async def test_verify_model_local_load_failure() -> None:
    """Model load failure skips all phases but still attempts cleanup unload."""
    entry = _build_local_entry()
    endpoint = _build_local_endpoint()

    with (
        patch(
            "rentl_core.compatibility.runner.load_lm_studio_model",
            side_effect=ModelLoadError("refused"),
        ),
        patch(
            "rentl_core.compatibility.runner.unload_lm_studio_model",
        ) as mock_unload,
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
    # Cleanup unload runs via finally even on load failure
    mock_unload.assert_awaited_once()


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
        patch(
            "rentl_core.compatibility.runner.unload_lm_studio_model",
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


async def test_verify_model_forwards_supports_tool_choice_required() -> None:
    """supports_tool_choice_required override is forwarded to create_model."""
    entry = VerifiedModelEntry(
        model_id="qwen/qwen3.5-27b",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
        config_overrides=VerifiedModelConfigOverrides(
            timeout_s=120.0,
            supports_tool_choice_required=False,
        ),
    )
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

        await verify_model(entry=entry, endpoint=endpoint)

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["supports_tool_choice_required"] is False


async def test_verify_model_forwards_max_output_retries() -> None:
    """max_output_retries override flows to Agent(output_retries=...)."""
    entry = VerifiedModelEntry(
        model_id="openai/gpt-oss-120b",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
        config_overrides=VerifiedModelConfigOverrides(
            timeout_s=120.0,
            max_output_retries=4,
        ),
    )
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

        await verify_model(entry=entry, endpoint=endpoint)

    # Agent should have been called 5 times (once per phase),
    # each with output_retries=4
    assert mock_agent_cls.call_count == 5
    for call in mock_agent_cls.call_args_list:
        assert call.kwargs.get("output_retries") == 4


async def test_verify_model_forwards_max_sdk_retries() -> None:
    """max_sdk_retries override flows to create_model(max_retries=...)."""
    entry = VerifiedModelEntry(
        model_id="minimax/minimax-m2.5",
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
        config_overrides=VerifiedModelConfigOverrides(
            timeout_s=2.0,
            max_sdk_retries=0,
        ),
    )
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

        await verify_model(entry=entry, endpoint=endpoint)

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["max_retries"] == 0


async def test_verify_model_max_sdk_retries_none_by_default() -> None:
    """max_sdk_retries defaults to None (SDK default) when not set."""
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

        await verify_model(entry=entry, endpoint=endpoint)

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["max_retries"] is None


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


async def test_verify_model_local_unloads_after_success() -> None:
    """Local model is unloaded after successful verification."""
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
        patch(
            "rentl_core.compatibility.runner.unload_lm_studio_model",
        ) as mock_unload,
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
    mock_load.assert_awaited_once()
    mock_unload.assert_awaited_once_with(
        load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
        model_id="google/gemma-3-27b",
        api_key="test-key",
        timeout_s=120.0,
    )


async def test_verify_model_local_unloads_after_phase_failure() -> None:
    """Local model is unloaded even when phases fail."""
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
        ),
        patch(
            "rentl_core.compatibility.runner.unload_lm_studio_model",
        ) as mock_unload,
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
            side_effect=RuntimeError("structured output failed"),
        )
        mock_agent_cls.return_value = mock_instance

        result = await verify_model(
            entry=entry,
            endpoint=endpoint,
        )

    assert result.passed is False
    mock_unload.assert_awaited_once()


async def test_verify_model_local_unload_failure_does_not_raise() -> None:
    """Unload failure after verification is logged but does not raise."""
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
        ),
        patch(
            "rentl_core.compatibility.runner.unload_lm_studio_model",
            side_effect=ModelUnloadError("unload failed"),
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

        # Should not raise despite unload failure
        result = await verify_model(
            entry=entry,
            endpoint=endpoint,
        )

    assert result.passed is True


async def test_verify_model_local_uses_load_timeout_for_load_and_unload() -> None:
    """load_timeout_s is used for load/unload, not timeout_s."""
    entry = VerifiedModelEntry(
        model_id="google/gemma-3-27b",
        endpoint_type="local",
        endpoint_ref="lm-studio",
        load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
        config_overrides=VerifiedModelConfigOverrides(
            timeout_s=5.0,
            load_timeout_s=90.0,
        ),
    )
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
        patch(
            "rentl_core.compatibility.runner.unload_lm_studio_model",
        ) as mock_unload,
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

        result = await verify_model(entry=entry, endpoint=endpoint)

    assert result.passed is True
    # Load uses load_timeout_s (90), NOT timeout_s (5)
    mock_load.assert_awaited_once_with(
        load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
        model_id="google/gemma-3-27b",
        api_key="test-key",
        timeout_s=90.0,
    )
    # Unload also uses load_timeout_s
    mock_unload.assert_awaited_once_with(
        load_endpoint="http://192.168.1.23:1234/api/v1/models/load",
        model_id="google/gemma-3-27b",
        api_key="test-key",
        timeout_s=90.0,
    )
    # Inference uses timeout_s (5), NOT load_timeout_s (90)
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["timeout_s"] == pytest.approx(5.0)


async def test_verify_model_openrouter_does_not_unload() -> None:
    """OpenRouter models do not trigger load or unload."""
    entry = _build_openrouter_entry()
    endpoint = _build_openrouter_endpoint()

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
        patch(
            "rentl_core.compatibility.runner.unload_lm_studio_model",
        ) as mock_unload,
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

    assert result.passed is True
    mock_load.assert_not_awaited()
    mock_unload.assert_not_awaited()
