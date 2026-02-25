# References: Comprehensive Token & Cost Tracking

## Issue
- https://github.com/trevorWieland/rentl/issues/141

## Key Implementation Files

### Token Schemas
- `packages/rentl-schemas/src/rentl_schemas/progress.py` — `AgentUsageTotals` (lines 45-52), `AgentTelemetry` (lines 65-114), `AgentTelemetrySummary` (lines 117-124)

### Token Aggregation (CLI)
- `services/rentl-cli/src/rentl/main.py` — `_aggregate_usage()` (lines 3150-3167), `_build_run_report_data()` (lines 3170-3228)

### Token Extraction (Agents)
- `packages/rentl-agents/src/rentl_agents/runtime.py` — `_build_usage_totals()` (lines 707-716)

### Token Aggregation (Core)
- `packages/rentl-core/src/rentl_core/status.py` — `_aggregate_agents()`, `_add_usage()` (lines 118-159)

### Telemetry Emission
- `packages/rentl-core/src/rentl_core/telemetry.py` — `AgentTelemetryEmitter` (lines 14-98)

### LLM Response Handling
- `packages/rentl-llm/src/rentl_llm/openai_runtime.py` — `OpenAICompatibleRuntime` (lines 15-72)

### New Files
- `packages/rentl-core/src/rentl_core/cost.py` — Cost aggregation logic (to be created)

## Dependencies
- s0.1.06 — Log/Event Taxonomy
- s0.1.10 — Phase Result Summaries & Metrics
- s0.1.27 — End-to-End Logging & Error Surfacing

## Benchmark Context
- `docs/benchmark-plan.md` — Full-game benchmark plan (blocks on this spec)
- `benchmark/karetoshi/configs/qwen3-full-pilot.toml` — Local model pilot config (demo step 2)
- `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml` — Cloud model pilot config (demo step 3)
