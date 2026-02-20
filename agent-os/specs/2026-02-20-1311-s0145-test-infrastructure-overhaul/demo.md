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

### Run 1 — Full demo (2026-02-20 19:45)
- Step 1 [RUN]: PASS — `make check` passes (993 unit tests, 95 integration tests, coverage thresholds met on both tiers)
- Step 2 [RUN]: PASS — `find packages -name 'test_*' -type f` returns nothing; `tests/features/` does not exist
- Step 3 [RUN]: PASS — grep for `_build_llm_runtime` and `pydantic_ai.Agent.run` in integration tests returns zero matches
- Step 4 [RUN]: PASS — all mocks in integration tests have corresponding invocation assertions (verified across 15 files with mocks)
- Step 5 [RUN]: PASS — Makefile quality target uses `--timeout=29` (≤30s)
- Step 6 [RUN]: PASS — `make quality` passes (9 tests in 37.82s, all within 29s individual timeout)
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 993 unit, 95 integration, 9 quality — all green)
- **Overall: PASS**

### Run 2 — Post-audit re-verification (2026-02-20 14:58)
- Step 1 [RUN]: PASS — `make check` passes (993 unit tests, coverage threshold met)
- Step 2 [RUN]: PASS — `find packages -name 'test_*' -type f` returns nothing; `tests/features/` does not exist
- Step 3 [RUN]: PASS — grep for `_build_llm_runtime` and `pydantic_ai.Agent.run` in integration tests returns zero matches
- Step 4 [RUN]: PASS — all mocks in integration tests have corresponding invocation assertions (verified across 18 files)
- Step 5 [RUN]: PASS — Makefile quality target uses `--timeout=29` (≤30s)
- Step 6 [RUN]: PASS — `make quality` passes (9 tests, all within 29s timeout)
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 993 unit, 95 integration, 9 quality — all green)
- **Overall: PASS**

### Run 3 — Post-audit re-verification (2026-02-20 15:22)
- Step 1 [RUN]: PASS — `make check` passes (993 unit tests, 95 integration tests, coverage thresholds met on both tiers)
- Step 2 [RUN]: PASS — `find packages -name 'test_*' -type f` returns nothing; `tests/features/` does not exist
- Step 3 [RUN]: PASS — grep for `_build_llm_runtime` and `pydantic_ai.Agent.run` in integration tests returns zero matches
- Step 4 [RUN]: PASS — all mocks in integration tests have corresponding invocation assertions (verified across 13 files with mocks)
- Step 5 [RUN]: PASS — Makefile quality target uses `--timeout=29` (≤30s)
- Step 6 [RUN]: PASS — `make quality` passes (9 tests, all within 29s timeout)
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 993 unit, 95 integration, 9 quality — all green)
- **Overall: PASS**

### Run 4 — Post-audit re-verification (2026-02-20 15:43)
- Step 1 [RUN]: PASS — `make check` passes (993 unit tests); `make integration` passes (95 integration tests, coverage thresholds met)
- Step 2 [RUN]: PASS — `find packages -name 'test_*' -type f` returns nothing; `tests/features/` does not exist
- Step 3 [RUN]: PASS — grep for `_build_llm_runtime` and `pydantic_ai.Agent.run` in integration tests returns zero matches
- Step 4 [RUN]: PASS — all mocks in integration tests have corresponding invocation assertions (verified across 11 files with mocks)
- Step 5 [RUN]: PASS — Makefile quality target uses `--timeout=29` (≤30s)
- Step 6 [RUN]: PASS — `make quality` passes (9 tests, all within 29s timeout)
- Step 7 [RUN]: PASS — `make all` passes (format, lint, type, 993 unit, 95 integration, 9 quality — all green)
- **Overall: PASS**

### Run 5 — Post-audit re-verification (2026-02-20 16:30)
- Step 1 [RUN]: PASS — `make check` passes (993 unit tests, coverage thresholds met)
- Step 2 [RUN]: PASS — `find packages -name 'test_*' -type f` returns nothing; `tests/features/` does not exist
- Step 3 [RUN]: PASS — grep for `_build_llm_runtime` and `pydantic_ai.Agent.run` in integration tests returns zero matches
- Step 4 [RUN]: PASS — all mocks in integration tests have corresponding invocation assertions (verified across 11 files with mocks)
- Step 5 [RUN]: PASS — Makefile quality target uses `--timeout=29` (≤30s)
- Step 6 [RUN]: FAIL — `make quality` failed: `test_pretranslation_agent_evaluation_passes` timed out at 29s (1 failed, 8 passed in 90.34s). Signpost 4 reopened.
- **Overall: FAIL**
