spec_id: s0.1.48
issue: https://github.com/trevorWieland/rentl/issues/141
version: v0.1

# Plan: Comprehensive Token & Cost Tracking

## Decision Record

Current `_aggregate_usage()` only counts COMPLETED agents, hiding real cost from failed/retried invocations. With the 5-model full-game benchmark imminent, we need complete token visibility and cost tracking before running 56K+ lines through different model configurations. USD cost relies on OpenRouter's reported cost field (not static pricing tables) plus optional per-model config overrides for custom setups.

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit on issue branch and push

- [x] Task 2: Extend Token Schemas for Status-Segmented Tracking
  - Add `SegmentedUsageTotals` schema to `packages/rentl-schemas/src/rentl_schemas/progress.py` with `completed`, `failed`, `retry` fields (each `AgentUsageTotals`)
  - Add optional `cost_usd: float | None` field to `AgentTelemetry`
  - Add optional `cost_usd: float | None` field to `AgentUsageTotals` for per-invocation cost
  - Unit tests for new schema construction and serialization
  - Acceptance: schemas validate with all combinations of present/absent cost data

- [x] Task 3: Update Usage Aggregation to Include All Statuses
  - Modify `_aggregate_usage()` in `services/rentl-cli/src/rentl/main.py` to count ALL agent statuses
  - Segment tokens into completed/failed/retry buckets based on `AgentTelemetry.status` and `attempt`
  - Update `_add_usage_totals()` helper to support segmented totals
  - Update `_aggregate_agents()` in `packages/rentl-core/src/rentl_core/status.py` consistently
  - Compute `waste_ratio` = (failed_tokens.total_tokens + retry_tokens.total_tokens) / grand_total_tokens
  - Unit tests for aggregation with mixed-status agents (completed, failed, retry combinations)
  - Unit tests for waste_ratio edge cases (zero total, all failed, all completed)

- [x] Task 4: Capture Cost Data from OpenRouter Responses
  - Investigate pydantic-ai's `RunResult` / `RunUsage` for cost metadata propagation
  - Extract cost from OpenRouter response and propagate through `AgentTelemetry.cost_usd`
  - Add optional per-model cost config fields (`input_cost_per_mtok`, `output_cost_per_mtok`) to run config schema
  - Create `packages/rentl-core/src/rentl_core/cost.py` with cost aggregation logic (sum per-phase, per-model)
  - Compute cost from config overrides when OpenRouter cost not available: `(input_tokens * input_price + output_tokens * output_price)`
  - Unit tests for cost extraction from mock OpenRouter responses
  - Unit tests for config-based cost calculation with known prices
  - Unit tests for graceful `null` cost when no pricing available

- [x] Task 5: Enhance Run Reports with Cost & Waste Data
  - Update `_build_run_report_data()` in `services/rentl-cli/src/rentl/main.py` to include:
    - `total_cost_usd` (float | null)
    - `cost_by_phase` (list of phase/cost breakdowns)
    - `waste_ratio` (float, 0.0 when no failures)
    - `tokens_failed` and `tokens_retried` (segmented totals)
  - Ensure cost data written to run report JSON artifact on disk
  - Unit tests for report structure with and without cost data

- [x] Task 6: Update CLI Status Display
  - Update `rentl status` token display to show cost summary when available
  - Show waste ratio in status output
  - Display "N/A" for cost when unavailable (local models)
  - Integration test for status display with cost data present
  - Integration test for status display with cost data absent (graceful degradation)

- [ ] Task 7: Integration Tests for End-to-End Cost Flow
  - BDD-style integration test: pipeline run with mocked LLM responses containing cost data → verify full flow from response → telemetry → report
  - BDD-style integration test: pipeline run without cost data → verify tokens tracked, cost fields null, no errors
  - Verify `waste_ratio` correct in report after mixed-status pipeline run
