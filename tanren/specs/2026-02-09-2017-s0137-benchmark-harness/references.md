# References: Benchmark Harness v0.1

## Implementation Files

- `packages/rentl-schemas/src/rentl_schemas/benchmark/` — New benchmark schema module (to be created)
- `packages/rentl-core/src/rentl_core/benchmark/` — New benchmark logic module (to be created)
- `services/rentl-cli/src/rentl_cli/main.py` — CLI router (add `benchmark` command)

## Existing Patterns to Follow

- `tests/quality/agents/quality_harness.py` — Quality test harness pattern (env vars, model config)
- `tests/quality/agents/evaluators.py` — Pydantic-evals evaluator pattern
- `tests/quality/agents/eval_types.py` — Eval data types
- `tests/quality/pipeline/test_golden_script_pipeline.py` — Full pipeline test pattern
- `tests/quality/agents/conftest.py` — Session-scoped fixture pattern

## External Dependencies

- KSRE (Katawa Shoujo Re-Engineered): https://github.com/fleetingheart/ksre
  - Japanese scripts: `tl_script_jp/` directory
  - English scripts: main game script files
  - License: MPL 2.0 (code), CC-BY-NC-ND (assets)

## Related Issues

- #37 — This spec (Benchmark Harness v0.1)
- #38 — s0.1.38 Benchmark Transparency Pack (depends on this spec)

## Dependency Specs

- s0.1.17 — Initial Phase Agent: Translate (Direct Translator) — DONE
- s0.1.19 — Initial Phase Agent: QA (Style Guide Critic) — DONE
- s0.1.20 — Initial Phase Agent: Edit — DONE
