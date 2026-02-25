spec_id: s0.1.48
issue: https://github.com/trevorWieland/rentl/issues/141
version: v0.1

# Spec: Comprehensive Token & Cost Tracking

## Problem

Current `_aggregate_usage()` only counts tokens from COMPLETED agents. Failed and retried agent invocations consume real tokens but are invisible in reports. No USD cost calculation exists. This must be in place before running full-game benchmarks so we can compare cost across models and pipeline configurations.

## Goals

- Track all tokens including failed and retried agents, with status-segmented breakdowns
- Compute USD cost from OpenRouter's reported cost field and optional per-model config overrides
- Enhance run reports with cost breakdown, waste ratio, and status-segmented token totals
- Persist cost data in run artifacts for benchmark comparison across 5 model configurations

## Non-Goals

- Building a comprehensive pricing table for all LLM providers (use OpenRouter's reported cost or config overrides only)
- Real-time cost alerting or budget limits
- Historical cost trend analysis across multiple runs (just per-run reporting)
- Cost optimization recommendations

## Acceptance Criteria

### Token Tracking
- [ ] `_aggregate_usage()` counts tokens from ALL agent statuses (COMPLETED, FAILED, retried), not just COMPLETED
- [ ] Token totals broken down by category: `completed_tokens`, `failed_tokens`, `retry_tokens` (each with input/output/total)
- [ ] `AgentUsageTotals` schema extended with status-segmented token fields
- [ ] Per-phase token breakdown includes all statuses

### Cost Calculation
- [ ] `AgentTelemetry` gains an optional `cost_usd` field, populated from OpenRouter's reported cost when available
- [ ] Config supports optional per-model cost override (`input_cost_per_mtok`, `output_cost_per_mtok`)
- [ ] Cost computed per-phase and per-model when pricing data exists
- [ ] When cost is unavailable (local models, no config override), cost fields are `null` — no errors

### Enhanced Run Reports
- [ ] `_build_run_report_data()` includes: `total_cost_usd`, `cost_by_phase`, `waste_ratio`, `tokens_failed`, `tokens_retried`
- [ ] `rentl status` displays cost summary when available (total cost, waste ratio)
- [ ] Cost data persisted in run report JSON artifacts for benchmark comparison

### Tests
- [ ] Unit tests for cost aggregation with known model prices and OpenRouter cost field
- [ ] Unit tests for aggregate usage including failed/retry agents
- [ ] Integration test showing cost appears in run report
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **All agent statuses counted** — `_aggregate_usage()` must include tokens from FAILED and retried agents, not just COMPLETED. The whole point is making invisible waste visible.
2. **Waste ratio always reported** — Every run report must include `waste_ratio` (failed+retry tokens / total tokens). A run with zero failures should show `0.0`, not omit the field.
3. **No hardcoded pricing tables** — USD cost comes from OpenRouter's reported cost field or user-defined config, never from a static pricing table that goes stale.
4. **Graceful degradation** — When cost data is unavailable (local models, unknown providers), the system must still report full token breakdowns. Cost fields show `null`, not an error.
5. **Cost data persisted in run artifacts** — Cost must be written to the run report JSON for benchmark comparison, not just displayed ephemerally.
