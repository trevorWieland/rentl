"""Quality tests for model compatibility verification.

Parametrized from the verified-models registry. Each registered model
is run through the full 5-phase mini-pipeline using the shared
verification runner from ``rentl_core.compatibility``.

No test skipping — missing env vars fail loudly.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from pytest_bdd import given, scenario, then, when

from rentl_core.compatibility import (
    ModelVerificationResult,
    PhaseVerificationStatus,
    verify_model,
)
from rentl_schemas.compatibility import VerifiedModelEntry
from rentl_schemas.config import ModelEndpointConfig
from tests.quality.compatibility.conftest import (
    _MODEL_ENTRIES,
    build_endpoint_for_entry,
)

pytestmark = pytest.mark.quality


# ---------------------------------------------------------------------------
# Registry-driven parametrized scenario
# ---------------------------------------------------------------------------

_FEATURE = "../features/compatibility/model_compatibility.feature"


@pytest.mark.parametrize(
    "model_entry",
    _MODEL_ENTRIES,
    ids=[e.model_id for e in _MODEL_ENTRIES],
    indirect=True,
)
@scenario(_FEATURE, "Verified model passes all pipeline phases")
def test_verified_model_passes_all_pipeline_phases(
    model_entry: VerifiedModelEntry,
) -> None:
    """Parametrized: one execution per registry model."""


# ---------------------------------------------------------------------------
# BDD context
# ---------------------------------------------------------------------------


@dataclass
class CompatibilityContext:
    """Mutable context bag for the compatibility BDD scenario."""

    entry: VerifiedModelEntry | None = None
    endpoint: ModelEndpointConfig | None = None
    result: ModelVerificationResult | None = None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


@given(
    "a verified model entry and its endpoint configuration",
    target_fixture="ctx",
)
def given_model_and_endpoint(
    model_entry: VerifiedModelEntry,
) -> CompatibilityContext:
    """Resolve the endpoint for the parametrized model entry.

    Returns:
        CompatibilityContext with entry and endpoint populated.
    """
    endpoint = build_endpoint_for_entry(model_entry)
    return CompatibilityContext(entry=model_entry, endpoint=endpoint)


@when("I run compatibility verification against the model")
def when_run_verification(ctx: CompatibilityContext) -> None:
    """Run the shared verification runner against the model."""
    assert ctx.entry is not None
    assert ctx.endpoint is not None
    ctx.result = asyncio.run(verify_model(entry=ctx.entry, endpoint=ctx.endpoint))


@then("all five pipeline phases pass")
def then_all_phases_pass(ctx: CompatibilityContext) -> None:
    """Assert every phase returned a PASSED status."""
    assert ctx.result is not None
    for phase_result in ctx.result.phase_results:
        assert phase_result.status == PhaseVerificationStatus.PASSED, (
            f"Model '{ctx.result.model_id}' failed phase "
            f"'{phase_result.phase}': {phase_result.error_message}"
        )


@then("the verification result reports overall success")
def then_overall_success(ctx: CompatibilityContext) -> None:
    """Assert the top-level passed flag is True."""
    assert ctx.result is not None
    assert ctx.result.passed, (
        f"Model '{ctx.result.model_id}' failed overall verification. "
        f"Phase results: {[r.model_dump() for r in ctx.result.phase_results]}"
    )
