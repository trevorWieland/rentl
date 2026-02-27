"""Unit tests for the model_entry fixture lifecycle in quality conftest.

Validates that the quality compatibility ``model_entry`` fixture correctly
manages LM Studio load/unload lifecycle for local models on success and
failure paths, including teardown unload guarantees.
"""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import tests.quality.compatibility.conftest as _compat_conftest

from rentl_core.compatibility.loader import ModelLoadError, ModelUnloadError
from rentl_schemas.compatibility import (
    VerifiedModelConfigOverrides,
    VerifiedModelEntry,
)

# Access the unwrapped generator function behind the @pytest.fixture decorator.
# pytest wraps fixture functions; __wrapped__ gives us the original generator.
_FixtureGen = Generator[VerifiedModelEntry]
_model_entry_fn: type[_FixtureGen] = _compat_conftest.model_entry.__wrapped__  # type: ignore[attr-defined]

_LOAD_ENDPOINT = "http://192.168.1.23:1234/api/v1/models/load"


def _build_local_entry(
    model_id: str = "google/gemma-3-27b",
    load_timeout_s: float | None = 120.0,
) -> VerifiedModelEntry:
    """Build a local VerifiedModelEntry for testing.

    Returns:
        A local model entry with the given parameters.
    """
    return VerifiedModelEntry(
        model_id=model_id,
        endpoint_type="local",
        endpoint_ref="lm-studio",
        load_endpoint=_LOAD_ENDPOINT,
        config_overrides=VerifiedModelConfigOverrides(
            timeout_s=5.0,
            load_timeout_s=load_timeout_s,
        ),
    )


def _build_openrouter_entry(
    model_id: str = "qwen/qwen3.5-27b",
) -> VerifiedModelEntry:
    """Build an OpenRouter VerifiedModelEntry for testing.

    Returns:
        An OpenRouter model entry with the given parameters.
    """
    return VerifiedModelEntry(
        model_id=model_id,
        endpoint_type="openrouter",
        endpoint_ref="openrouter",
        config_overrides=VerifiedModelConfigOverrides(timeout_s=3.0),
    )


def _fake_request(param: VerifiedModelEntry) -> SimpleNamespace:
    """Build a minimal request-like object for indirect parametrize fixtures.

    Returns:
        SimpleNamespace with a ``param`` attribute matching pytest's FixtureRequest.
    """
    return SimpleNamespace(param=param)


# ---------------------------------------------------------------------------
# Local model: success path
# ---------------------------------------------------------------------------


def test_local_fixture_calls_load_and_unload_on_success() -> None:
    """model_entry loads model before yield and unloads in teardown on success."""
    entry = _build_local_entry()
    request = _fake_request(entry)

    mock_load = AsyncMock()
    mock_unload = AsyncMock()

    with (
        patch(
            "tests.quality.compatibility.conftest.load_lm_studio_model",
            mock_load,
        ),
        patch(
            "tests.quality.compatibility.conftest.unload_lm_studio_model",
            mock_unload,
        ),
        patch.dict(
            "os.environ",
            {"RENTL_LOCAL_API_KEY": "test-key"},
        ),
    ):
        gen = _model_entry_fn(request)
        yielded = next(gen)

        # Verify load was called with correct args
        mock_load.assert_awaited_once_with(
            load_endpoint=_LOAD_ENDPOINT,
            model_id="google/gemma-3-27b",
            api_key="test-key",
            timeout_s=120.0,
        )

        # Yielded value is the entry
        assert yielded is entry

        # Unload not yet called
        mock_unload.assert_not_awaited()

        # Finish the generator (simulate test completion)
        with pytest.raises(StopIteration):
            next(gen)

    # Unload called in teardown
    mock_unload.assert_awaited_once_with(
        load_endpoint=_LOAD_ENDPOINT,
        model_id="google/gemma-3-27b",
        api_key="test-key",
        timeout_s=120.0,
    )


# ---------------------------------------------------------------------------
# Local model: test failure path (exception during test body)
# ---------------------------------------------------------------------------


def test_local_fixture_unloads_on_test_failure() -> None:
    """model_entry unloads the model even when the test body raises."""
    entry = _build_local_entry()
    request = _fake_request(entry)

    mock_load = AsyncMock()
    mock_unload = AsyncMock()

    with (
        patch(
            "tests.quality.compatibility.conftest.load_lm_studio_model",
            mock_load,
        ),
        patch(
            "tests.quality.compatibility.conftest.unload_lm_studio_model",
            mock_unload,
        ),
        patch.dict(
            "os.environ",
            {"RENTL_LOCAL_API_KEY": "test-key"},
        ),
    ):
        gen = _model_entry_fn(request)
        next(gen)

        # Simulate a test body raising an exception
        with pytest.raises(AssertionError, match="simulated test failure"):
            gen.throw(AssertionError("simulated test failure"))

    # Unload must still be called despite the test failure
    mock_unload.assert_awaited_once()


# ---------------------------------------------------------------------------
# Local model: load failure path
# ---------------------------------------------------------------------------


def test_local_fixture_propagates_load_error() -> None:
    """model_entry propagates ModelLoadError when load fails."""
    entry = _build_local_entry()
    request = _fake_request(entry)

    mock_load = AsyncMock(side_effect=ModelLoadError("load failed"))
    mock_unload = AsyncMock()

    with (
        patch(
            "tests.quality.compatibility.conftest.load_lm_studio_model",
            mock_load,
        ),
        patch(
            "tests.quality.compatibility.conftest.unload_lm_studio_model",
            mock_unload,
        ),
        patch.dict(
            "os.environ",
            {"RENTL_LOCAL_API_KEY": "test-key"},
        ),
        pytest.raises(ModelLoadError, match="load failed"),
    ):
        gen = _model_entry_fn(request)
        next(gen)

    # Load was attempted
    mock_load.assert_awaited_once()


# ---------------------------------------------------------------------------
# Local model: unload failure during teardown (swallowed)
# ---------------------------------------------------------------------------


def test_local_fixture_swallows_unload_error_in_teardown() -> None:
    """model_entry logs but swallows ModelUnloadError during teardown."""
    entry = _build_local_entry()
    request = _fake_request(entry)

    mock_load = AsyncMock()
    mock_unload = AsyncMock(side_effect=ModelUnloadError("unload failed"))

    with (
        patch(
            "tests.quality.compatibility.conftest.load_lm_studio_model",
            mock_load,
        ),
        patch(
            "tests.quality.compatibility.conftest.unload_lm_studio_model",
            mock_unload,
        ),
        patch.dict(
            "os.environ",
            {"RENTL_LOCAL_API_KEY": "test-key"},
        ),
    ):
        gen = _model_entry_fn(request)
        yielded = next(gen)
        assert yielded is entry

        # Teardown should not raise even though unload fails
        with pytest.raises(StopIteration):
            next(gen)

    mock_unload.assert_awaited_once()


# ---------------------------------------------------------------------------
# Local model: load_timeout_s uses default when not set
# ---------------------------------------------------------------------------


def test_local_fixture_uses_default_load_timeout() -> None:
    """model_entry falls back to 120s load timeout when load_timeout_s is None."""
    entry = _build_local_entry(load_timeout_s=None)
    request = _fake_request(entry)

    mock_load = AsyncMock()
    mock_unload = AsyncMock()

    with (
        patch(
            "tests.quality.compatibility.conftest.load_lm_studio_model",
            mock_load,
        ),
        patch(
            "tests.quality.compatibility.conftest.unload_lm_studio_model",
            mock_unload,
        ),
        patch.dict(
            "os.environ",
            {"RENTL_LOCAL_API_KEY": "test-key"},
        ),
    ):
        gen = _model_entry_fn(request)
        next(gen)

        # Verify load was called with the 120.0 default timeout
        mock_load.assert_awaited_once_with(
            load_endpoint=_LOAD_ENDPOINT,
            model_id="google/gemma-3-27b",
            api_key="test-key",
            timeout_s=120.0,
        )

        with pytest.raises(StopIteration):
            next(gen)


# ---------------------------------------------------------------------------
# OpenRouter model: no lifecycle calls
# ---------------------------------------------------------------------------


def test_openrouter_fixture_skips_load_unload() -> None:
    """model_entry yields OpenRouter entries without any LM Studio lifecycle."""
    entry = _build_openrouter_entry()
    request = _fake_request(entry)

    mock_load = AsyncMock()
    mock_unload = AsyncMock()

    with (
        patch(
            "tests.quality.compatibility.conftest.load_lm_studio_model",
            mock_load,
        ),
        patch(
            "tests.quality.compatibility.conftest.unload_lm_studio_model",
            mock_unload,
        ),
        patch.dict(
            "os.environ",
            {"RENTL_OPENROUTER_API_KEY": "test-key"},
        ),
    ):
        gen = _model_entry_fn(request)
        yielded = next(gen)
        assert yielded is entry

        with pytest.raises(StopIteration):
            next(gen)

    mock_load.assert_not_awaited()
    mock_unload.assert_not_awaited()


# ---------------------------------------------------------------------------
# Missing env var: fails loudly
# ---------------------------------------------------------------------------


def test_local_fixture_fails_on_missing_env_var() -> None:
    """model_entry raises RuntimeError when RENTL_LOCAL_API_KEY is missing."""
    entry = _build_local_entry()
    request = _fake_request(entry)

    with (
        patch(
            "tests.quality.compatibility.conftest._load_env_file",
        ),
        patch.dict(
            "os.environ",
            {},
            clear=True,
        ),
        pytest.raises(RuntimeError, match="RENTL_LOCAL_API_KEY"),
    ):
        gen = _model_entry_fn(request)
        next(gen)


def test_openrouter_fixture_fails_on_missing_env_var() -> None:
    """model_entry raises RuntimeError when RENTL_OPENROUTER_API_KEY is missing."""
    entry = _build_openrouter_entry()
    request = _fake_request(entry)

    with (
        patch(
            "tests.quality.compatibility.conftest._load_env_file",
        ),
        patch.dict(
            "os.environ",
            {},
            clear=True,
        ),
        pytest.raises(RuntimeError, match="RENTL_OPENROUTER_API_KEY"),
    ):
        gen = _model_entry_fn(request)
        next(gen)
