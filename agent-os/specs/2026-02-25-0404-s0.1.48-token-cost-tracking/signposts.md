# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---

## Signpost 1: OpenRouter cost not accessible through pydantic-ai

- **Task:** 4
- **Status:** resolved
- **Problem:** pydantic-ai's `RunUsage` does not propagate OpenRouter's native cost data. OpenRouter includes cost in the API response `usage` object, but the OpenAI SDK's `CompletionUsage` Pydantic model doesn't define a `cost` field, so it's silently dropped during parsing. Additionally, pydantic-ai's `_map_usage()` function in `pydantic_ai/models/openai.py` filters the `details` dict to only include `int` values (line 2881: `if isinstance(v, int)`), which excludes any float cost values.
- **Evidence:**
  - `CompletionUsage` only has `completion_tokens`, `prompt_tokens`, `total_tokens` + detail sub-objects — no `cost` field
  - pydantic-ai `_map_usage` at line 2881: `if isinstance(v, int)` filters out floats
  - `genai_prices` has OpenRouter pricing data but spec non-negotiable #3 prohibits static pricing tables
- **Tried:** Investigated `RunUsage.details`, `RequestUsage.extract()`, `genai_prices.calc_price()`, OpenAI SDK's `CompletionUsage`
- **Solution:** Implemented config-based cost calculation via `input_cost_per_mtok` / `output_cost_per_mtok` fields on `ModelSettings`. When both are set, cost is computed as `(input_tokens * input_price + output_tokens * output_price) / 1M`. When neither is set, `cost_usd` is `None` (graceful degradation). The code is structured so that if pydantic-ai adds cost propagation in the future, it can be easily integrated.
- **Resolution:** do-task round 1 (Task 4)
- **Files affected:** `packages/rentl-agents/src/rentl_agents/runtime.py`, `packages/rentl-schemas/src/rentl_schemas/config.py`

## Signpost 2: Status-cost BDD fixtures violate ProgressUpdate validator

- **Task:** 6
- **Status:** resolved
- **Problem:** The new Task 6 integration fixtures construct `ProgressUpdate` with `phase_status=running` while the attached `phase_progress.status` is `completed`. `ProgressUpdate` validates these fields must match, so both scenarios fail before executing CLI assertions.
- **Evidence:**
  - Command: `pytest -q tests/integration/cli/test_status_cost.py`
  - Error: `Value error, phase_status does not match phase_progress.status`
  - Mismatch locations: `tests/integration/cli/test_status_cost.py:203` and `tests/integration/cli/test_status_cost.py:258` (`phase_status=PhaseStatus.RUNNING`) with `tests/integration/cli/test_status_cost.py:111` (`status=PhaseStatus.COMPLETED`)
- **Impact:** Task 6 integration coverage is currently broken, so cost/waste status behavior is not verified and the task cannot be considered complete.
- **Solution:** Changed `phase_status=PhaseStatus.RUNNING` to `phase_status=PhaseStatus.COMPLETED` in both fixture functions to match the `phase_progress.status`. Also added two new BDD scenarios for non-JSON display: verifying cost row with dollar amount, cost row with N/A, and waste row with percentage.
- **Resolution:** do-task round 2 (Task 6)
- **Files affected:** `tests/integration/cli/test_status_cost.py`, `tests/integration/features/cli/status_cost.feature`

## Signpost 3: Quality pipeline test intermittent timeout at 29s

- **Task:** post-completion (make all gate)
- **Status:** resolved
- **Problem:** `test_translate_phase_produces_translated_output` in `tests/quality/pipeline/test_golden_script_pipeline.py` timed out at 29s during `make all`. The module-level `pytestmark = pytest.mark.timeout(29)` was 1s tighter than the standard-mandated 30s limit, causing intermittent failures when the LLM API response was slow. The spec changes (cost tracking) did not affect the pipeline execution path — the timeout was a pre-existing fragility.
- **Evidence:**
  - `make all` output: `FAILED tests/quality/pipeline/test_golden_script_pipeline.py::test_translate_phase_produces_translated_output - Failed: Timeout (>29.0s) from pytest-timeout.`
  - Stack trace showed hang in `asyncio base_events.py _selector.poll()` — waiting for LLM API I/O
  - Re-run with 60s timeout passed in 3.82s — confirming intermittent API latency, not a regression
  - `git diff` of all spec changes confirmed no modifications to async pipeline execution path
- **Tried:** Investigated whether spec changes caused a regression — confirmed they did not
- **Solution:** Removed the module-level `pytestmark = pytest.mark.timeout(29)`. The global `timeout = 30` from `pyproject.toml` already enforces the <30s quality test standard. Additionally, reduced endpoint `timeout_s` from 10 to 8 (matching `quality_harness` pattern) to leave ~22s headroom for pipeline overhead within the 30s budget.
- **Resolution:** do-task fix rounds (post-Task 7, third pass)
- **Files affected:** `tests/quality/pipeline/test_golden_script_pipeline.py`

## Signpost 4: Makefile quality target timeout 1s too tight

- **Task:** post-completion (make all gate)
- **Status:** resolved
- **Problem:** The Makefile `quality` target passes `--timeout=29` to pytest, 1s tighter than the standard-mandated 30s limit. `test_pretranslation_agent_evaluation_passes` involves both an agent run and an `LLMJudge` evaluation (two LLM round-trips), which intermittently exceeds 29s due to API latency. Same root cause as Signpost 3 but at the Makefile level rather than per-test level.
- **Evidence:**
  - `make all` output: `FAILED tests/quality/agents/test_pretranslation_agent.py::test_pretranslation_agent_evaluation_passes - Failed: Timeout (>29.0s) from pytest-timeout.`
  - Stack trace: hang in `asyncio base_events._selector.poll()` — waiting for LLM API I/O
  - Makefile line 79: `--timeout=29` overrides pyproject.toml's `timeout = 30`
  - Standard `test-timing-rules` specifies quality tests `<30s`, not `<29s`
- **Tried:** Verified this is a pre-existing Makefile issue, not caused by spec changes
- **Solution:** Changed `--timeout=29` to `--timeout=30` in Makefile quality target to match the standard and pyproject.toml
- **Resolution:** do-task fix round (post-Task 7, second pass)
- **Files affected:** `Makefile`

## Signpost 5: Deepseek benchmark config missing cost pricing fields

- **Task:** Demo Step 3 / Task 8
- **Status:** resolved
- **Problem:** Demo step 3 expects `total_cost_usd` populated in the deepseek run report, but it's `null`. The implementation correctly computes cost from config-based `input_cost_per_mtok` / `output_cost_per_mtok` fields (see Signpost 1 for why OpenRouter's native cost isn't accessible). However, the benchmark config `deepseek-mtl-pilot.toml` doesn't set these pricing fields, so cost gracefully degrades to `null`.
- **Evidence:**
  - Command: `uv run rentl run-pipeline -c benchmark/karetoshi/configs/deepseek-mtl-pilot.toml`
  - Run report at `benchmark/karetoshi/runs/deepseek-mtl-pilot/logs/reports/019c934c-8907-7147-bab7-91877641e216.json`
  - `total_cost_usd: null`, `cost_by_phase: [{"phase": "translate", "cost_usd": null}]`
  - Config has no `input_cost_per_mtok` or `output_cost_per_mtok` in `[pipeline.default_model]` or `[pipeline.phases.model]`
  - Code path in `runtime.py:764`: `if input_cost_per_mtok is None or output_cost_per_mtok is None: return None`
- **Root cause:** Config gap, not code gap. The benchmark config needs pricing fields for `deepseek/deepseek-v3.2` model to enable cost calculation.
- **Solution:** Added `input_cost_per_mtok = 0.30` and `output_cost_per_mtok = 0.88` to both `[pipeline.default_model]` and `[pipeline.phases.model]` (translate phase) in the benchmark config.
- **Resolution:** do-task round 1 (Task 8)
- **Files affected:** `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml`

## Signpost 6: AgentUsageTotals drops cache and reasoning tokens from RunUsage

- **Task:** 9
- **Status:** resolved
- **Problem:** `AgentUsageTotals` only captures `input_tokens`, `output_tokens`, `total_tokens`, `request_count`, `tool_calls`, and `cost_usd`. pydantic-ai's `RunUsage` also provides `cache_read_tokens`, `cache_write_tokens` (top-level fields), and `reasoning_tokens` (in the `details` dict). These are silently dropped in `_build_usage_totals`, meaning cost reports understate cache savings and reasoning overhead.
- **Evidence:**
  - `AgentUsageTotals` fields at `packages/rentl-schemas/src/rentl_schemas/progress.py:45-55`: only `input_tokens`, `output_tokens`, `total_tokens`, `request_count`, `tool_calls`, `cost_usd`
  - `_build_usage_totals` at `packages/rentl-agents/src/rentl_agents/runtime.py:728-749`: maps only `usage.input_tokens`, `usage.output_tokens`, `usage.total_tokens`, `usage.requests`, `usage.tool_calls`
  - pydantic-ai `RunUsage` at `.venv/lib/python3.14/site-packages/pydantic_ai/usage.py:169-201`: defines `cache_write_tokens: int = 0`, `cache_read_tokens: int = 0` as top-level fields, plus `details: dict[str, int]` which contains `reasoning_tokens` when present
  - Discovered during walk-spec demo walkthrough: reviewing `_build_usage_totals` mapping against `RunUsage` definition
  - Audit round 1 (Task 9): `uv run pytest -q tests/unit/schemas/test_progress.py -k cache_and_reasoning` fails with `AttributeError: 'AgentUsageTotals' object has no attribute 'cache_read_tokens'` (3 failed)
  - Audit round 1 (Task 9): `uv run pytest -q tests/unit/rentl-agents/test_runtime_cost.py -k 'maps_cache_tokens or maps_reasoning_tokens'` fails with missing `cache_read_tokens` and `reasoning_tokens` (2 failed)
- **Impact:** Token visibility is incomplete — cache hit/miss ratios and reasoning token overhead are invisible in run reports, which matters for cost optimization and model comparison in the benchmark suite.
- **Solution:** Add the three fields to `AgentUsageTotals`, map them in `_build_usage_totals`, sum them in aggregation helpers, and include them in report JSON serialization. No CLI display changes needed (total_tokens is the right summary). No tiered cache pricing (future work).
- **Resolution:** do-task round 3 (Task 9). Added fields to schema, mapped in `_build_usage_totals`, summed in `_add_usage`/`_add_usage_totals`, serialized in report JSON. All tests pass.
- **Files affected:** `packages/rentl-schemas/src/rentl_schemas/progress.py`, `packages/rentl-agents/src/rentl_agents/runtime.py`, `packages/rentl-core/src/rentl_core/status.py`, `services/rentl-cli/src/rentl/main.py`

## Signpost 7: DeepSeek V3.2 pricing drift after Task 8

- **Task:** 8
- **Status:** resolved
- **Problem:** Task 8 requires verifying current OpenRouter pricing before setting config overrides, but the benchmark config still uses stale rates (`0.30` input / `0.88` output) instead of the current model-page rates.
- **Evidence:**
  - `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml:50-51` and `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml:129-130` set `input_cost_per_mtok = 0.30` and `output_cost_per_mtok = 0.88`
  - OpenRouter model page `https://openrouter.ai/deepseek/deepseek-v3.2` (checked 2026-02-25) shows `Input: $0.25/M` and `Output: $0.40/M`
  - DeepSeek run report `benchmark/karetoshi/runs/deepseek-mtl-pilot/logs/reports/019c9520-adec-77cc-a75e-2145afdd0744.json` currently computes `total_cost_usd = 0.045994780000000006` from the stale overrides
- **Impact:** Cost totals are overstated relative to current provider pricing, reducing benchmark comparability across model configs.
- **Solution:** Updated config overrides to `input_cost_per_mtok = 0.25` and `output_cost_per_mtok = 0.40` at all 4 locations. Re-ran pipeline — new report `019c95b9-a766-76c9-bd89-4ad3e826a927.json` shows `total_cost_usd = 0.0367315` (down from `0.045994780000000006` with stale rates).
- **Resolution:** do-task round 2 (Task 8)
- **Files affected:** `benchmark/karetoshi/configs/deepseek-mtl-pilot.toml`
