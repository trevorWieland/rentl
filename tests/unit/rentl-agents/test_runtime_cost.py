"""Tests for cost extraction in the agent runtime."""

from __future__ import annotations

import pytest
from pydantic_ai.usage import RunUsage

from rentl_agents.runtime import _build_usage_totals, _compute_cost_usd  # noqa: PLC2701

# --- _compute_cost_usd ---


def test_compute_cost_usd_with_config() -> None:
    """Compute cost when both price fields are provided."""
    cost = _compute_cost_usd(
        input_tokens=1_000_000,
        output_tokens=500_000,
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
    )
    assert cost == pytest.approx(10.5)


def test_compute_cost_usd_none_when_no_input_price() -> None:
    """Return None when input price is missing."""
    cost = _compute_cost_usd(
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_mtok=None,
        output_cost_per_mtok=15.0,
    )
    assert cost is None


def test_compute_cost_usd_none_when_no_output_price() -> None:
    """Return None when output price is missing."""
    cost = _compute_cost_usd(
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=None,
    )
    assert cost is None


def test_compute_cost_usd_none_when_no_prices() -> None:
    """Return None when both prices are missing."""
    cost = _compute_cost_usd(
        input_tokens=1000,
        output_tokens=500,
        input_cost_per_mtok=None,
        output_cost_per_mtok=None,
    )
    assert cost is None


def test_compute_cost_usd_zero_tokens() -> None:
    """Zero tokens produce zero cost."""
    cost = _compute_cost_usd(
        input_tokens=0,
        output_tokens=0,
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
    )
    assert cost == pytest.approx(0.0)


# --- _build_usage_totals ---


def test_build_usage_totals_none_usage() -> None:
    """Return None when usage is None."""
    result = _build_usage_totals(None)
    assert result is None


def test_build_usage_totals_empty_usage() -> None:
    """Return None when usage has no values."""
    result = _build_usage_totals(RunUsage())
    assert result is None


def test_build_usage_totals_without_cost() -> None:
    """Build usage totals without cost config — cost_usd is None."""
    usage = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    result = _build_usage_totals(usage)
    assert result is not None
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.total_tokens == 150
    assert result.request_count == 1
    assert result.cost_usd is None


def test_build_usage_totals_with_cost_config() -> None:
    """Build usage totals with cost config — cost_usd computed."""
    usage = RunUsage(input_tokens=1000, output_tokens=500, requests=1)
    result = _build_usage_totals(
        usage,
        input_cost_per_mtok=3.0,
        output_cost_per_mtok=15.0,
    )
    assert result is not None
    assert result.input_tokens == 1000
    assert result.output_tokens == 500
    # 1000 * 3.0 / 1M + 500 * 15.0 / 1M = 0.003 + 0.0075 = 0.0105
    assert result.cost_usd == pytest.approx(0.0105)


def test_build_usage_totals_partial_cost_config() -> None:
    """Build usage totals with only input price — cost_usd is None."""
    usage = RunUsage(input_tokens=1000, output_tokens=500, requests=1)
    result = _build_usage_totals(
        usage,
        input_cost_per_mtok=3.0,
    )
    assert result is not None
    assert result.cost_usd is None


# --- cache and reasoning token mapping ---


def test_build_usage_totals_maps_cache_tokens() -> None:
    """Map cache_read_tokens and cache_write_tokens from RunUsage."""
    usage = RunUsage(
        input_tokens=100,
        output_tokens=50,
        requests=1,
        cache_read_tokens=30,
        cache_write_tokens=20,
    )
    result = _build_usage_totals(usage)
    assert result is not None
    assert result.cache_read_tokens == 30
    assert result.cache_write_tokens == 20


def test_build_usage_totals_maps_reasoning_tokens_from_details() -> None:
    """Build usage totals extracts reasoning_tokens from RunUsage.details dict."""
    usage = RunUsage(
        input_tokens=100,
        output_tokens=50,
        requests=1,
        details={"reasoning_tokens": 42},
    )
    result = _build_usage_totals(usage)
    assert result is not None
    assert result.reasoning_tokens == 42


def test_build_usage_totals_reasoning_defaults_zero_when_absent() -> None:
    """Build usage totals defaults reasoning_tokens to 0 when not in details."""
    usage = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    result = _build_usage_totals(usage)
    assert result is not None
    assert result.reasoning_tokens == 0


def test_build_usage_totals_cache_defaults_zero() -> None:
    """Build usage totals defaults cache tokens to 0 when RunUsage has defaults."""
    usage = RunUsage(input_tokens=100, output_tokens=50, requests=1)
    result = _build_usage_totals(usage)
    assert result is not None
    assert result.cache_read_tokens == 0
    assert result.cache_write_tokens == 0
