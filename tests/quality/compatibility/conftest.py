"""Shared fixtures for model compatibility quality tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from rentl_schemas.compatibility import (
    VerifiedModelEntry,
    VerifiedModelRegistry,
    load_bundled_registry,
)
from rentl_schemas.config import ModelEndpointConfig

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
            api_key_env="LM_STUDIO_API_KEY",
            timeout_s=180.0,
        )

    raise ValueError(
        f"Unknown endpoint_ref '{entry.endpoint_ref}' for model "
        f"'{entry.model_id}'. Expected 'openrouter' or 'lm-studio'."
    )


def load_registry_and_validate_env() -> tuple[VerifiedModelRegistry, dict[str, bool]]:
    """Load the bundled registry and validate that env vars exist.

    Validates that the required API key env vars are set for each
    endpoint type present in the registry. Fails loudly — no skipping.

    Returns:
        Tuple of (registry, mapping of endpoint_ref to env-ready bool).
    """
    _load_env_file()
    registry = load_bundled_registry()

    endpoint_refs = {e.endpoint_ref for e in registry.models}

    if "openrouter" in endpoint_refs:
        _require_env("RENTL_OPENROUTER_API_KEY")
    if "lm-studio" in endpoint_refs:
        _require_env("LM_STUDIO_API_KEY")

    return registry, dict.fromkeys(endpoint_refs, True)


# ---------------------------------------------------------------------------
# Registry-driven model entries (used by test parametrization)
# ---------------------------------------------------------------------------

_REGISTRY, _ENV_STATUS = load_registry_and_validate_env()
_MODEL_ENTRIES: list[VerifiedModelEntry] = list(_REGISTRY.models)


@pytest.fixture()
def model_entry(request: pytest.FixtureRequest) -> VerifiedModelEntry:
    """Return the current model entry from indirect parametrization.

    The test module applies ``@pytest.mark.parametrize(..., indirect=True)``
    which sets ``request.param`` to a ``VerifiedModelEntry`` for each model.
    """
    entry: VerifiedModelEntry = request.param
    return entry
