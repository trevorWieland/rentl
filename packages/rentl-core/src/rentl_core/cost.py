"""Cost aggregation logic for token usage.

Computes per-phase and per-model USD cost from AgentTelemetry records.
Cost data comes from config-based per-model pricing or provider-reported cost.
When no pricing is available, cost fields are None (graceful degradation).
"""

from __future__ import annotations

from rentl_schemas.primitives import PhaseName
from rentl_schemas.progress import (
    AgentTelemetry,
    SegmentedUsageTotals,
)


def compute_cost_from_config(
    *,
    input_tokens: int,
    output_tokens: int,
    input_cost_per_mtok: float,
    output_cost_per_mtok: float,
) -> float:
    """Compute USD cost from token counts and per-million-token pricing.

    Args:
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens consumed.
        input_cost_per_mtok: Input cost per million tokens (USD).
        output_cost_per_mtok: Output cost per million tokens (USD).

    Returns:
        Computed cost in USD.
    """
    return (
        input_tokens * input_cost_per_mtok + output_tokens * output_cost_per_mtok
    ) / 1_000_000


def aggregate_cost_by_phase(
    agents: list[AgentTelemetry],
) -> dict[PhaseName, float | None]:
    """Aggregate cost by phase from agent telemetry records.

    Sums cost_usd from each agent's telemetry (or usage.cost_usd) grouped by phase.
    Returns None for a phase if no cost data is available for any agent in that phase.

    Args:
        agents: List of agent telemetry records.

    Returns:
        Mapping of phase name to total cost (or None when unavailable).
    """
    phase_costs: dict[PhaseName, float | None] = {}
    for agent in agents:
        phase = agent.phase
        cost = _extract_agent_cost(agent)
        if cost is not None:
            phase_costs[phase] = (phase_costs.get(phase) or 0.0) + cost
        elif phase not in phase_costs:
            phase_costs[phase] = None
    return phase_costs


def aggregate_total_cost(agents: list[AgentTelemetry]) -> float | None:
    """Aggregate total cost from all agent telemetry records.

    Returns None if no agent has cost data.

    Args:
        agents: List of agent telemetry records.

    Returns:
        Total cost in USD, or None when unavailable.
    """
    total: float | None = None
    for agent in agents:
        cost = _extract_agent_cost(agent)
        if cost is not None:
            total = (total or 0.0) + cost
    return total


def aggregate_segmented_cost(
    segmented: SegmentedUsageTotals,
) -> tuple[float | None, float | None, float | None]:
    """Extract cost from segmented usage totals.

    Args:
        segmented: Status-segmented usage totals.

    Returns:
        Tuple of (completed_cost, failed_cost, retry_cost), each None when unavailable.
    """
    return (
        segmented.completed.cost_usd,
        segmented.failed.cost_usd,
        segmented.retry.cost_usd,
    )


def _extract_agent_cost(agent: AgentTelemetry) -> float | None:
    """Extract cost from an agent telemetry record.

    Prefers agent-level cost_usd, falls back to usage.cost_usd.

    Returns:
        Cost in USD, or None when unavailable.
    """
    if agent.cost_usd is not None:
        return agent.cost_usd
    if agent.usage is not None and agent.usage.cost_usd is not None:
        return agent.usage.cost_usd
    return None
