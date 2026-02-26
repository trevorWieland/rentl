"""BDD integration tests for shipped rentl.toml multi-endpoint configuration.

Validates that the shipped config defines both openrouter and lm-studio
endpoints so that ``rentl verify-models`` can resolve endpoint refs for
all registry models without programmatic endpoint construction.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from rentl_schemas.compatibility import (
    VerifiedModelRegistry,
    load_bundled_registry,
)
from rentl_schemas.config import ModelEndpointConfig, RunConfig
from rentl_schemas.validation import validate_run_config

pytestmark = pytest.mark.integration

scenarios("../features/cli/verify_models_config.feature")

_REPO_ROOT = Path(__file__).resolve().parents[3]


class _ConfigCtx:
    """Shared state for BDD steps."""

    config: RunConfig
    endpoints_map: dict[str, ModelEndpointConfig]
    registry: VerifiedModelRegistry
    unresolved_refs: list[str]


@pytest.fixture()
def ctx() -> _ConfigCtx:
    """Return fresh BDD context."""
    return _ConfigCtx()


# ── Given ──────────────────────────────────────────────────────────────


@given("the shipped rentl.toml config", target_fixture="ctx")
def given_shipped_config(ctx: _ConfigCtx) -> _ConfigCtx:
    """Load the shipped rentl.toml from the repo root.

    Returns:
        Populated BDD context with loaded config and endpoints map.
    """
    config_path = _REPO_ROOT / "rentl.toml"
    with open(config_path, "rb") as fh:
        payload = tomllib.load(fh)
    ctx.config = validate_run_config(payload)
    ctx.endpoints_map = {}
    if ctx.config.endpoints is not None:
        for ep in ctx.config.endpoints.endpoints:
            ctx.endpoints_map[ep.provider_name] = ep
    elif ctx.config.endpoint is not None:
        ctx.endpoints_map[ctx.config.endpoint.provider_name] = ctx.config.endpoint
    return ctx


@given("the bundled verified-models registry")
def given_bundled_registry(ctx: _ConfigCtx) -> None:
    """Load the bundled verified-models registry."""
    ctx.registry = load_bundled_registry()


# ── When ───────────────────────────────────────────────────────────────


@when("the config is loaded and validated")
def when_config_validated(ctx: _ConfigCtx) -> None:
    """Config was already validated in the Given step; nothing extra needed."""


@when("each registry model's endpoint_ref is looked up")
def when_lookup_endpoint_refs(ctx: _ConfigCtx) -> None:
    """Look up each registry model's endpoint_ref in the config endpoints."""
    ctx.unresolved_refs = [
        f"{entry.model_id} -> {entry.endpoint_ref}"
        for entry in ctx.registry.models
        if entry.endpoint_ref not in ctx.endpoints_map
    ]


# ── Then ───────────────────────────────────────────────────────────────


@then('the config contains an "openrouter" endpoint')
def then_has_openrouter(ctx: _ConfigCtx) -> None:
    """Assert the openrouter endpoint is configured."""
    assert "openrouter" in ctx.endpoints_map, (
        f"Expected 'openrouter' endpoint, got: {sorted(ctx.endpoints_map)}"
    )


@then('the config contains a "lm-studio" endpoint')
def then_has_lm_studio(ctx: _ConfigCtx) -> None:
    """Assert the lm-studio endpoint is configured."""
    assert "lm-studio" in ctx.endpoints_map, (
        f"Expected 'lm-studio' endpoint, got: {sorted(ctx.endpoints_map)}"
    )


@then('the default endpoint is "openrouter"')
def then_default_is_openrouter(ctx: _ConfigCtx) -> None:
    """Assert the default endpoint ref is openrouter."""
    assert ctx.config.endpoints is not None
    assert ctx.config.endpoints.default == "openrouter"


@then("every endpoint_ref maps to a configured endpoint")
def then_all_refs_resolve(ctx: _ConfigCtx) -> None:
    """Assert no registry endpoint_ref is unresolved."""
    assert ctx.unresolved_refs == [], f"Unresolved endpoint refs: {ctx.unresolved_refs}"
