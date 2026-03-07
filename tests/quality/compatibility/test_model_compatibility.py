"""Quality tests for model compatibility verification.

Parametrized from the verified-models registry. Each registered model x
pipeline phase combination gets its own test case (9 models x 5 phases =
45 tests), so each test makes a single LLM call and easily fits within
the 45s quality timeout.

No test skipping — missing env vars fail loudly.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from pytest_bdd import given, scenario, then, when

from rentl_core.compatibility import (
    PhaseResult,
    PhaseVerificationStatus,
    verify_single_phase,
)
from rentl_schemas.compatibility import VerifiedModelEntry
from rentl_schemas.config import ModelEndpointConfig
from rentl_schemas.primitives import PhaseName
from tests.quality.compatibility.conftest import (
    _MODEL_ENTRIES,
    _PHASE_NAMES,
    build_endpoint_for_entry,
)

pytestmark = pytest.mark.quality


# ---------------------------------------------------------------------------
# Registry-driven parametrized scenario: per model x per phase
# ---------------------------------------------------------------------------

_FEATURE = "../features/compatibility/model_compatibility.feature"


@pytest.mark.parametrize(
    "phase_name",
    _PHASE_NAMES,
    ids=[p.value for p in _PHASE_NAMES],
    indirect=True,
)
@pytest.mark.parametrize(
    "model_entry",
    _MODEL_ENTRIES,
    ids=[e.model_id for e in _MODEL_ENTRIES],
    indirect=True,
)
@scenario(_FEATURE, "Verified model passes a single pipeline phase")
def test_verified_model_passes_phase(
    model_entry: VerifiedModelEntry,
    phase_name: PhaseName,
) -> None:
    """Parametrized: one execution per registry model x pipeline phase."""


# ---------------------------------------------------------------------------
# BDD context
# ---------------------------------------------------------------------------


@dataclass
class PhaseCompatibilityContext:
    """Mutable context bag for the per-phase compatibility BDD scenario."""

    entry: VerifiedModelEntry | None = None
    endpoint: ModelEndpointConfig | None = None
    phase: PhaseName | None = None
    result: PhaseResult | None = None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


@given(
    "a verified model entry and its endpoint configuration",
    target_fixture="ctx",
)
def given_model_and_endpoint(
    model_entry: VerifiedModelEntry,
    phase_name: PhaseName,
) -> PhaseCompatibilityContext:
    """Resolve the endpoint for the parametrized model entry.

    Returns:
        PhaseCompatibilityContext with entry, endpoint, and phase populated.
    """
    endpoint = build_endpoint_for_entry(model_entry)
    return PhaseCompatibilityContext(
        entry=model_entry, endpoint=endpoint, phase=phase_name
    )


@when("I run single-phase compatibility verification against the model")
def when_run_single_phase_verification(ctx: PhaseCompatibilityContext) -> None:
    """Run the shared single-phase verification runner against the model."""
    assert ctx.entry is not None
    assert ctx.endpoint is not None
    assert ctx.phase is not None
    ctx.result = asyncio.run(
        verify_single_phase(
            entry=ctx.entry,
            endpoint=ctx.endpoint,
            phase_name=ctx.phase,
        )
    )


@then("the pipeline phase passes")
def then_phase_passes(ctx: PhaseCompatibilityContext) -> None:
    """Assert the phase returned a PASSED status."""
    assert ctx.result is not None
    assert ctx.result.status == PhaseVerificationStatus.PASSED, (
        f"Model '{ctx.entry.model_id if ctx.entry else '?'}' failed phase "
        f"'{ctx.result.phase}': {ctx.result.error_message}"
    )
