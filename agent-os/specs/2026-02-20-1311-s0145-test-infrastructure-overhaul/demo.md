# Demo: Test Infrastructure Overhaul

The test suite now conforms to all 5 testing standards — proper mock boundaries, coverage enforcement, timing limits, three-tier structure, and BDD style. This demo proves the restructured infrastructure works end-to-end and that no violations remain.

## Environment

- API keys: RENTL_OPENROUTER_API_KEY via .env
- External services:
  - OpenRouter API at https://openrouter.ai/api/v1 — verified (200)
- Setup: none

## Steps

1. **[RUN]** Run `make check` (unit + integration) — expected: all tests pass, coverage threshold met on both tiers
2. **[RUN]** Verify no test files exist outside `tests/{unit,integration,quality}/` — expected: `find packages -name 'test_*' -type f` returns nothing, `tests/features/` directory doesn't exist
3. **[RUN]** Grep integration tests for forbidden mock targets (`_build_llm_runtime`, `pydantic_ai.Agent.run`) — expected: zero matches
4. **[RUN]** Grep integration tests for mock invocation assertions — expected: every mock has a corresponding assert
5. **[RUN]** Verify Makefile quality timeout is ≤30s — expected: `--timeout=30` or lower in quality target
6. **[RUN]** Run `make quality` — expected: all quality tests pass within 30s timeout
7. **[RUN]** Run `make all` — expected: full gate passes

## Results

(Appended by run-demo — do not write this section during shaping)
