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
  - [x] Fix: Align `phase_status` and `phase_progress.status` in status-cost fixtures to satisfy `ProgressUpdate` validation (`tests/integration/cli/test_status_cost.py:203`, `tests/integration/cli/test_status_cost.py:258`) (audit round 1; see signposts.md: Task 6, status/phase mismatch in BDD fixtures)
  - [x] Fix: Add integration assertions for non-JSON `rentl status` display rows (`cost` and `waste`), including `"N/A"` when cost is unavailable, to cover Task 6 display requirements (`tests/integration/cli/test_status_cost.py`, `services/rentl-cli/src/rentl/main.py:3473`) (audit round 1)

- [x] Task 7: Integration Tests for End-to-End Cost Flow
  - BDD-style integration test: pipeline run with mocked LLM responses containing cost data → verify full flow from response → telemetry → report
  - BDD-style integration test: pipeline run without cost data → verify tokens tracked, cost fields null, no errors
  - Verify `waste_ratio` correct in report after mixed-status pipeline run

- [x] Task 8: Add cost pricing to deepseek benchmark config
  - Add `input_cost_per_mtok` and `output_cost_per_mtok` to `deepseek-mtl-pilot.toml` model settings for `deepseek/deepseek-v3.2`
  - Look up current DeepSeek V3.2 pricing on OpenRouter (input: $0.30/Mtok, output: $0.88/Mtok as of Feb 2026 — verify before setting)
  - After adding pricing, re-run `uv run rentl run-pipeline -c benchmark/karetoshi/configs/deepseek-mtl-pilot.toml` to verify `total_cost_usd` is populated in the run report
  - See signposts.md Signpost 5 for full context
  - [x] Fix: Update DeepSeek V3.2 pricing overrides in `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml:50`, `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml:51`, `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml:129`, and `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml:130` to match current OpenRouter rates (audit round 1; see signposts.md: Signpost 7, pricing drift)
  - [x] Fix: Re-run `uv run rentl run-pipeline -c benchmark/karetoshi/configs/deepseek-mtl-pilot.toml` and record the new run report evidence for `total_cost_usd` in `signposts.md` (audit round 1; see signposts.md: Signpost 7, pricing drift)

- [x] Task 9: Add cache and reasoning token tracking to AgentUsageTotals
  - Add `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens` fields to `AgentUsageTotals` schema (`packages/rentl-schemas/src/rentl_schemas/progress.py:45`)
  - Map fields in `_build_usage_totals` from pydantic-ai's `RunUsage` (`packages/rentl-agents/src/rentl_agents/runtime.py:728`): `cache_read_tokens` and `cache_write_tokens` are top-level fields; `reasoning_tokens` is in `usage.details` dict
  - Update `_add_usage_totals` (`services/rentl-cli/src/rentl/main.py:3139`) and `_add_usage` (`packages/rentl-core/src/rentl_core/status.py:162`) to sum new fields
  - Update JSON serialization: `_usage_segment_dict`, `token_usage` dict, `usage_by_phase_entries` in `_build_run_report_data` (`services/rentl-cli/src/rentl/main.py:3249-3302`)
  - Unit tests for schema construction, field mapping from RunUsage, and aggregation summation
  - Integration test assertions for new fields in report JSON
  - Do NOT change CLI status display (total_tokens is the right summary)
  - Do NOT add tiered cache pricing logic (track fields for visibility, cost accuracy is future work)
  - See signposts.md Signpost 6 for full context
