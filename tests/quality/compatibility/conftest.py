"""Shared fixtures for model compatibility quality tests."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv

from rentl_core.compatibility import (
    PHASE_CONFIGS,
    load_lm_studio_model,
    unload_lm_studio_model,
)
from rentl_core.compatibility.loader import ModelLoadError, ModelUnloadError
from rentl_schemas.compatibility import (
    VerifiedModelEntry,
    VerifiedModelRegistry,
    load_bundled_registry,
)
from rentl_schemas.config import ModelEndpointConfig
from rentl_schemas.primitives import PhaseName

_log = logging.getLogger(__name__)

_LM_STUDIO_DEFAULT_BASE_URL = "http://192.168.1.23:1234/v1"


def _load_env_file() -> None:
    """Load environment variables from the repo .env file if present."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _require_env(name: str) -> str:
    """Read a required environment variable, raising on missing.

    Args:
        name: Environment variable name.

    Returns:
        The variable value.

    Raises:
        RuntimeError: When the variable is absent or empty.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Compatibility quality tests require {name}. "
            f"Set it in your .env file or shell environment."
        )
    return value


def build_endpoint_for_entry(
    entry: VerifiedModelEntry,
) -> ModelEndpointConfig:
    """Build a ModelEndpointConfig matching a registry entry's endpoint_ref.

    Args:
        entry: The verified model entry to build an endpoint for.

    Returns:
        Resolved endpoint configuration.

    Raises:
        ValueError: When endpoint_ref is unrecognised.
    """
    if entry.endpoint_ref == "openrouter":
        return ModelEndpointConfig(
            provider_name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="RENTL_OPENROUTER_API_KEY",
        )

    if entry.endpoint_ref == "lm-studio":
        base_url = os.getenv("RENTL_LM_STUDIO_BASE_URL", _LM_STUDIO_DEFAULT_BASE_URL)
        return ModelEndpointConfig(
            provider_name="lm-studio",
            base_url=base_url,
            api_key_env="RENTL_LOCAL_API_KEY",
            timeout_s=5.0,
        )

    raise ValueError(
        f"Unknown endpoint_ref '{entry.endpoint_ref}' for model "
        f"'{entry.model_id}'. Expected 'openrouter' or 'lm-studio'."
    )


def validate_env_for_registry(registry: VerifiedModelRegistry) -> dict[str, bool]:
    """Validate that required API key env vars are set for the registry.

    Checks that the required API key env vars are set for each
    endpoint type present in the registry. Fails loudly — no skipping.

    Args:
        registry: The loaded verified model registry.

    Returns:
        Mapping of endpoint_ref to env-ready bool.
    """
    _load_env_file()

    endpoint_refs = {e.endpoint_ref for e in registry.models}

    if "openrouter" in endpoint_refs:
        _require_env("RENTL_OPENROUTER_API_KEY")
    if "lm-studio" in endpoint_refs:
        _require_env("RENTL_LOCAL_API_KEY")

    return dict.fromkeys(endpoint_refs, True)


# ---------------------------------------------------------------------------
# Registry-driven model entries (used by test parametrization)
# ---------------------------------------------------------------------------
# NOTE: Registry loading (TOML parse) happens at import time so
# @pytest.mark.parametrize can enumerate models during collection.
# Env-var validation is deferred to a session-scoped fixture so that
# collection never crashes — tests fail at runtime instead.

_REGISTRY: VerifiedModelRegistry = load_bundled_registry()
_MODEL_ENTRIES: list[VerifiedModelEntry] = list(_REGISTRY.models)

# All pipeline phase names for per-phase parametrization
_PHASE_NAMES: list[PhaseName] = [phase for phase, _, _, _ in PHASE_CONFIGS]


@pytest.fixture()
def model_entry(request: pytest.FixtureRequest) -> Generator[VerifiedModelEntry]:
    """Yield the current model entry with LM Studio lifecycle management.

    The test module applies ``@pytest.mark.parametrize(..., indirect=True)``
    which sets ``request.param`` to a ``VerifiedModelEntry`` for each model.

    Validates required env vars at test time (not collection time) so
    collection never crashes. Tests fail loudly at setup if env vars are
    missing — no skipping.

    For local (LM Studio) models, manages the full load/unload lifecycle
    per Task 7 single-model residency guarantees.

    ``verify_single_phase`` delegates local lifecycle to callers, so this
    fixture is the quality-test integration point for that contract.

    Yields:
        The parametrized ``VerifiedModelEntry`` for the current test case.

    Raises:
        ModelLoadError: When LM Studio model loading fails.
        ValueError: When ``endpoint_ref`` is not recognised.
    """
    _load_env_file()
    entry: VerifiedModelEntry = request.param

    if entry.endpoint_ref == "openrouter":
        _require_env("RENTL_OPENROUTER_API_KEY")
        yield entry
        return

    if entry.endpoint_ref == "lm-studio":
        api_key = _require_env("RENTL_LOCAL_API_KEY")

        # Resolve load timeout (decoupled from per-phase inference timeout)
        load_timeout = (
            entry.config_overrides.load_timeout_s
            if entry.config_overrides.load_timeout_s is not None
            else 120.0
        )

        # Load model before test (resource-aware: unloads others first)
        if entry.load_endpoint is not None:
            try:
                asyncio.run(
                    load_lm_studio_model(
                        load_endpoint=entry.load_endpoint,
                        model_id=entry.model_id,
                        api_key=api_key,
                        timeout_s=load_timeout,
                    )
                )
            except ModelLoadError:
                _log.exception("Failed to load model %s before test", entry.model_id)
                raise

        try:
            yield entry
        finally:
            # Always unload after test to free GPU memory
            if entry.load_endpoint is not None:
                try:
                    asyncio.run(
                        unload_lm_studio_model(
                            load_endpoint=entry.load_endpoint,
                            model_id=entry.model_id,
                            api_key=api_key,
                            timeout_s=load_timeout,
                        )
                    )
                except ModelUnloadError:
                    _log.warning(
                        "Failed to unload model %s after test",
                        entry.model_id,
                    )
        return

    # Unknown endpoint_ref — fail loudly
    raise ValueError(
        f"Unknown endpoint_ref '{entry.endpoint_ref}' for model '{entry.model_id}'."
    )


@pytest.fixture()
def phase_name(request: pytest.FixtureRequest) -> PhaseName:
    """Return the current phase name from indirect parametrization."""
    return request.param
