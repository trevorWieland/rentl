# Demo: Comprehensive Token & Cost Tracking

Token and cost tracking makes invisible waste visible. Currently, failed and retried agent invocations consume real tokens but aren't reported — they represent real cost that's invisible in run reports. This spec adds status-segmented token tracking, OpenRouter cost integration, and waste ratio computation. We'll prove it works end-to-end on real pipeline runs — a local model (qwen3 via LM Studio) and a cloud model (deepseek MTL via OpenRouter) — then verify run reports have the full cost/token picture for benchmark comparison.

## Environment

- API keys: `RENTL_OPENROUTER_API_KEY` via `.env` (OpenRouter cloud), `RENTL_LOCAL_API_KEY` via `.env` (LM Studio local)
- External services:
  - OpenRouter API at https://openrouter.ai/api/v1 — verified (200)
  - LM Studio at http://192.168.1.23:1234/v1 — verified (200)
- Setup: none (benchmark pilot configs already prepared)

## Steps

1. **[RUN]** Run `make all` — expected: all unit/integration tests pass, including new cost/token tracking tests. Zero test failures.

2. **[RUN]** Run `uv run rentl run-pipeline -c benchmark/karetoshi/configs/qwen3-full-pilot.toml` to completion — expected: pipeline completes on 322 pilot lines, run report JSON contains full token breakdown (`completed_tokens`, `failed_tokens`, `retry_tokens`), cost fields are `null` (local model has no pricing), `waste_ratio` computed (0.0 if no failures).

3. **[RUN]** Run `uv run rentl run-pipeline -c benchmark/karetoshi/configs/deepseek-mtl-pilot.toml` to completion — expected: pipeline completes on 322 pilot lines, run report JSON contains full token breakdown AND `total_cost_usd` populated from OpenRouter's reported cost, `cost_by_phase` populated with per-phase USD costs.

4. **[RUN]** Run `uv run rentl status` on both completed runs — expected: cost summary displays for deepseek run (shows USD total and per-phase cost), graceful "N/A" for qwen3 local run (shows tokens but no cost), waste_ratio shown for both runs.

## Results

(Appended by run-demo — do not write this section during shaping)
