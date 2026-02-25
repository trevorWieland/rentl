"""Unit tests for rentl_core.cost module."""

from __future__ import annotations

import pytest

from rentl_core.cost import (
    aggregate_cost_by_phase,
    aggregate_segmented_cost,
    aggregate_total_cost,
    compute_cost_from_config,
)
from rentl_schemas.primitives import PhaseName
from rentl_schemas.progress import (
    AgentStatus,
    AgentTelemetry,
    AgentUsageTotals,
    SegmentedUsageTotals,
)

# --- compute_cost_from_config ---


def test_compute_cost_from_config_basic() -> None:
    """Compute cost from known per-million-token prices."""
    cost = compute_cost_from_config(
        input_tokens=1_000_000,
        output_tokens=500_000,
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
    )
    # 1M * 3.0/1M + 500K * 15.0/1M = 3.0 + 7.5 = 10.5
    assert cost == pytest.approx(10.5)


def test_compute_cost_from_config_zero_tokens() -> None:
    """Zero tokens produce zero cost."""
    cost = compute_cost_from_config(
        input_tokens=0,
        output_tokens=0,
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
    )
    assert cost == pytest.approx(0.0)


def test_compute_cost_from_config_small_tokens() -> None:
    """Small token counts produce fractional cost."""
    cost = compute_cost_from_config(
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
    )
    # 1000 * 3.0 / 1M + 500 * 15.0 / 1M = 0.003 + 0.0075 = 0.0105
    assert cost == pytest.approx(0.0105)


# --- aggregate_cost_by_phase ---


def _make_agent(
    phase: PhaseName,
    cost_usd: float | None = None,
    usage_cost: float | None = None,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> AgentTelemetry:
    usage = AgentUsageTotals(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=usage_cost,
    )
    return AgentTelemetry(
        agent_run_id="cost_test_agent",
        agent_name="test_agent",
        phase=phase,
        status=AgentStatus.COMPLETED,
        cost_usd=cost_usd,
        usage=usage,
    )


def test_aggregate_cost_by_phase_with_costs() -> None:
    """Aggregate cost grouped by phase."""
    agents = [
        _make_agent(PhaseName.TRANSLATE, cost_usd=0.01),
        _make_agent(PhaseName.TRANSLATE, cost_usd=0.02),
        _make_agent(PhaseName.CONTEXT, cost_usd=0.005),
    ]
    result = aggregate_cost_by_phase(agents)
    assert result[PhaseName.TRANSLATE] == pytest.approx(0.03)
    assert result[PhaseName.CONTEXT] == pytest.approx(0.005)


def test_aggregate_cost_by_phase_no_costs() -> None:
    """Phase with no cost data returns None."""
    agents = [
        _make_agent(PhaseName.TRANSLATE),
    ]
    result = aggregate_cost_by_phase(agents)
    assert result[PhaseName.TRANSLATE] is None


def test_aggregate_cost_by_phase_mixed_availability() -> None:
    """Phase with some agents having cost and others not sums available cost."""
    agents = [
        _make_agent(PhaseName.TRANSLATE, cost_usd=0.01),
        _make_agent(PhaseName.TRANSLATE),  # No cost
    ]
    result = aggregate_cost_by_phase(agents)
    # Only the agent with cost contributes
    assert result[PhaseName.TRANSLATE] == pytest.approx(0.01)


def test_aggregate_cost_by_phase_fallback_to_usage_cost() -> None:
    """Falls back to usage.cost_usd when agent-level cost_usd is None."""
    agents = [
        _make_agent(PhaseName.TRANSLATE, usage_cost=0.015),
    ]
    result = aggregate_cost_by_phase(agents)
    assert result[PhaseName.TRANSLATE] == pytest.approx(0.015)


# --- aggregate_total_cost ---


def test_aggregate_total_cost_with_costs() -> None:
    """Sum total cost from all agents."""
    agents = [
        _make_agent(PhaseName.TRANSLATE, cost_usd=0.01),
        _make_agent(PhaseName.CONTEXT, cost_usd=0.005),
    ]
    total = aggregate_total_cost(agents)
    assert total == pytest.approx(0.015)


def test_aggregate_total_cost_no_costs() -> None:
    """Returns None when no agent has cost."""
    agents = [
        _make_agent(PhaseName.TRANSLATE),
    ]
    total = aggregate_total_cost(agents)
    assert total is None


def test_aggregate_total_cost_empty() -> None:
    """Returns None for empty agent list."""
    total = aggregate_total_cost([])
    assert total is None


# --- aggregate_segmented_cost ---


def test_aggregate_segmented_cost_all_present() -> None:
    """Extract cost from all segments."""
    segmented = SegmentedUsageTotals(
        completed=AgentUsageTotals(total_tokens=100, cost_usd=0.05),
        failed=AgentUsageTotals(total_tokens=50, cost_usd=0.02),
        retry=AgentUsageTotals(total_tokens=30, cost_usd=0.01),
    )
    completed, failed, retry = aggregate_segmented_cost(segmented)
    assert completed == pytest.approx(0.05)
    assert failed == pytest.approx(0.02)
    assert retry == pytest.approx(0.01)


def test_aggregate_segmented_cost_none_when_unavailable() -> None:
    """Segments without cost return None."""
    segmented = SegmentedUsageTotals()
    completed, failed, retry = aggregate_segmented_cost(segmented)
    assert completed is None
    assert failed is None
    assert retry is None
