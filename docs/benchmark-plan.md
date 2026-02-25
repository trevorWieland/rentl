# Full-Game Benchmark Plan: Karetoshi x 5 Models

**Date:** 2026-02-23
**Status:** Data prepared, configs ready, awaiting s0.1.48 before execution

---

## Context

v0.1 is nearly complete (s0.1.38 + s0.1.47 remaining). Before wrapping up and moving to v0.2, we want to run the full pipeline on a real game (`karetoshi.xlsx`) with 5 model configurations to: (a) benchmark quality across models, (b) stress-test the pipeline at scale, (c) track full token/cost data, (d) generate game patches for qualitative human evaluation, and (e) mine actionable roadmap items from the experience.

**Constraints:**
- LM Studio at `http://192.168.1.23:1234/v1` -- only one local model loaded at a time
- Local models: gpt-oss-20b (currently loaded), qwen3-vl-30b, gemma-3-27b
- Cloud: deepseek/deepseek-v3.2 via OpenRouter
- Full judge comparison on all lines

---

## Data: karetoshi.xlsx

- **290 worksheets**, ~114,500 total rows
- **Scene sheets (271):** Named `seenXXXX.ss` (e.g., `seen2010.ss`)
- **Character sheets (12):** `_aduki_lv1.ss`, `_ichika_lv2.ss`, etc. (placeholder content only)
- **System sheets (7):** `_costume.ss`, `_extra.ss`, `_start.ss`, `__define.ss`, etc.
- **4 columns:** Index (int), Text (JP), Translation (placeholder copy), Empty
- **Speaker/dialogue pattern:** Speaker name rows alternate with dialogue/narration
- **56,340 translatable content lines** (after excluding 56,556 speaker metadata rows)
- **Largest scene:** `seen_3160` (1,134 content lines)

### Conversion Results

| Metric | Value |
|--------|-------|
| Total sheets | 290 |
| Included (scene sheets) | 271 |
| Excluded | 19 |
| Speaker metadata rows | 56,556 |
| Content lines emitted | 56,340 |
| Pilot slice (3 scenes) | 322 lines |
| Line ID validation | All pass `^[a-z]+(?:_[0-9]+)+$` |
| SourceLine schema validation | All 56,340 pass |

**Files:**
- `benchmark/karetoshi/data/karetoshi.jsonl` -- full game (56,340 lines)
- `benchmark/karetoshi/data/karetoshi_pilot.jsonl` -- pilot slice (322 lines, scenes: seen_1000, seen_2000, seen_2010)
- `benchmark/karetoshi/convert_xlsx.py` -- conversion script (reproducible)

---

## 5 Model Configurations

| Config | Endpoint | Model ID | Pipeline | Concurrency |
|--------|----------|----------|----------|-------------|
| `gpt-oss-full.toml` | LM Studio (local) | `openai/gpt-oss-20b` | All 7 phases | Low (2 req, 1 scene) |
| `qwen3-full.toml` | LM Studio (local) | `qwen/qwen3-vl-30b` | All 7 phases | Low (2 req, 1 scene) |
| `gemma3-full.toml` | LM Studio (local) | `google/gemma-3-27b` | All 7 phases | Low (2 req, 1 scene) |
| `deepseek-mtl.toml` | OpenRouter | `deepseek/deepseek-v3.2` | ingest+translate+export | High (8 req, 4 scenes) |
| `deepseek-full.toml` | OpenRouter | `deepseek/deepseek-v3.2` | All 7 phases | High (8 req, 4 scenes) |

All configs validated against `RunConfig` schema. Model IDs need verification against LM Studio's `/v1/models` endpoint before execution.

Local configs: `timeout_s = 600`, `max_retries = 3`, `backoff_s = 5.0`.
MTL config: context, pretranslation, qa, edit all set `enabled = false`.

**Files:** `benchmark/karetoshi/configs/*.toml`

---

## Execution Plan (After Today)

### Phase 1: Spec s0.1.48 -- Token & Cost Tracking
- GitHub issue: https://github.com/trevorWieland/rentl/issues/141
- Track all tokens including failures/retries, compute USD costs, enhance run reports
- **Must complete before full game runs**

### Phase 2: Pilot Validation (3 scenes, 322 lines)
- Run all 5 configs on `karetoshi_pilot.jsonl`
- Order: deepseek-mtl -> gpt-oss -> qwen3 -> gemma3 -> deepseek-full
- Fix any issues before proceeding to full game

### Phase 3: Full Game Runs (56,340 lines)
- Sequential, cheapest first: deepseek-mtl -> gpt-oss -> qwen3 -> gemma3 -> deepseek-full
- Use `--run-id` for resume on failures
- Switch local models in LM Studio between runs

### Phase 4: Automated Benchmark
- 5 candidates -> 10 pairwise comparisons via `rentl benchmark compare`
- Key comparison: deepseek-full vs deepseek-mtl (same model, different pipeline = isolates pipeline value)
- Judge model: local gpt-oss-20b via LM Studio (free, just GPU time)
- Scale estimate: ~56K lines x 10 pairs = 560K judge calls (significant time, zero API cost)
- If full-game judging is too slow, fall back to sampling representative scenes

### Phase 5: Cost Analysis + Qualitative Eval + Roadmap Items
- Cost comparison across 5 configs (requires s0.1.48)
- Human evaluation of sample scenes from each config
- Mine roadmap items for v0.2 from the benchmark experience

---

## Spec Line Items

### s0.1.48: Comprehensive Token & Cost Tracking (NEW)
- **What:** Track all agent invocations (including FAILED/RETRIED), compute USD costs from model pricing data, enhance run reports with cost breakdown and waste ratio.
- **Why:** Current `_aggregate_usage()` only counts COMPLETED agents. Failed/retried tokens are invisible. No USD cost calculation exists. Must have before benchmark runs.
- **Depends on:** s0.1.06, s0.1.10, s0.1.27
- **Issue:** https://github.com/trevorWieland/rentl/issues/141
- **Key files:** `services/rentl-cli/src/rentl/main.py`, `packages/rentl-schemas/src/rentl_schemas/progress.py`, new `packages/rentl-core/src/rentl_core/cost.py`

### s0.1.38: Benchmark Transparency Pack (existing)
- The benchmark exercise will naturally produce the artifacts for this spec
- Should be completed alongside or right after the benchmark runs

---

## Verification Checklist

- [x] `karetoshi.jsonl` validates against SourceLine schema (56,340/56,340 pass)
- [x] All line_ids match `^[a-z]+(?:_[0-9]+)+$`
- [x] All 5 .toml configs load without validation errors
- [x] s0.1.48 added to roadmap
- [x] s0.1.48 GitHub issue created (#141)
- [x] Plan document stored in `docs/benchmark-plan.md`
