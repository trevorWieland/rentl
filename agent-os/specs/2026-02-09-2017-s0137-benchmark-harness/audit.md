status: fail
fix_now_count: 3

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-10
- Round: 3

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 4/5
- Completion: 3/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — eval text is downloaded at runtime (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:33`), and tracked eval-set assets are config/hash files only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`; `git ls-files packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/*`).
2. **Apples-to-apples comparison**: **PASS** — compare validates matching line IDs across all candidates before judging (`services/rentl-cli/src/rentl_cli/main.py:1313`, `packages/rentl-core/src/rentl_core/benchmark/output_loader.py:67`) and evaluates all candidate pairs under one shared judge/runtime configuration (`services/rentl-cli/src/rentl_cli/main.py:1329`, `services/rentl-cli/src/rentl_cli/main.py:1365`).
3. **Scores must include per-line evidence**: **PASS** — reasoning is required by schema (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`), required by parser (`packages/rentl-core/src/rentl_core/benchmark/judge.py:129`), and emitted per line in report head-to-head results (`services/rentl-cli/src/rentl_cli/main.py:1455`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:51`).
4. **Benchmark runnable standalone**: **PASS** — standalone CLI commands exist and are discoverable (`services/rentl-cli/src/rentl_cli/main.py:1099`, `services/rentl-cli/src/rentl_cli/main.py:1228`; command output `uv run rentl benchmark --help` shows `download` and `compare`).

## Demo Status
- Latest run: **PASS** (Run 4, 2026-02-10)
- `demo.md` records Step 1 passing and Steps 2-5 skipped with explicit external-service rationale (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:48`).
- Full verification gate was rerun in this audit: `make all` passed (format/lint/type + 805 unit + 81 integration + quality stage green).

## Standards Adherence
- `testing/three-tier-test-structure`: **PASS** — benchmark coverage is in `tests/unit`, `tests/integration`, and `tests/quality` (`tests/unit/benchmark/test_output_loader.py:1`, `tests/integration/benchmark/test_cli_command.py:1`, `tests/quality/benchmark/test_benchmark_quality.py:1`; standard `agent-os/standards/testing/three-tier-test-structure.md:3`).
- `testing/no-mocks-for-quality-tests`: **PASS** — quality compare scenario runs real CLI compare without mocked judge runtime (`tests/quality/benchmark/test_benchmark_quality.py:134`; standard `agent-os/standards/testing/no-mocks-for-quality-tests.md:41`).
- `testing/bdd-for-integration-quality`: **PASS** — integration and quality scenarios use Given/When/Then BDD flow (`tests/integration/benchmark/test_cli_command.py:20`, `tests/quality/benchmark/test_benchmark_quality.py:34`; standard `agent-os/standards/testing/bdd-for-integration-quality.md:3`).
- `python/pydantic-only-schemas`: **PASS** — benchmark schema contracts are Pydantic `BaseModel` types (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`; standard `agent-os/standards/python/pydantic-only-schemas.md:3`).
- `python/async-first-design`: **PASS** — compare path uses async/structured concurrency (`services/rentl-cli/src/rentl_cli/main.py:1273`, `services/rentl-cli/src/rentl_cli/main.py:1420`; standard `agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — schema fields are typed with `Field(description=...)` (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`, `packages/rentl-schemas/src/rentl_schemas/benchmark/config.py:62`; standard `agent-os/standards/python/strict-typing-enforcement.md:32`).
- `ux/trust-through-transparency`: **violation (Medium)** — progress reporting is non-monotonic because completion uses task index (`services/rentl-cli/src/rentl_cli/main.py:1417`), violating progress visibility/explainability requirements (`agent-os/standards/ux/trust-through-transparency.md:69`).
- `testing/validate-generated-artifacts`: **PASS** — quality flow schema-validates generated report artifacts (`tests/quality/benchmark/test_benchmark_quality.py:169`; standard `agent-os/standards/testing/validate-generated-artifacts.md:10`).

## Regression Check
- Unresolved signpost regression remains open: progress accounting still uses index-based updates (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:114`, `services/rentl-cli/src/rentl_cli/main.py:1417`).
- Prior spec-audit round 2 Fix Now items persist unchanged: stale dead benchmark path and winner-label mismatch are still present (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:50`, `services/rentl-cli/src/rentl_cli/main.py:2590`, `tests/quality/benchmark/test_benchmark_quality.py:214`).
- No regressions found in resolved signposts for Task 3 hash/slice/parser fixes; benchmark eval-set unit/integration suites still pass (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:12`, test run `pytest -q tests/unit/benchmark tests/integration/benchmark` -> `110 passed`).

## Action Items

### Fix Now
- Fix progress accounting in benchmark compare to update by completed-task count (monotonic), not task index, and add out-of-order completion regression coverage (`services/rentl-cli/src/rentl_cli/main.py:1417`, `tests/integration/benchmark/test_cli_command.py:1`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:114`).
- Remove stale monolithic `_run_benchmark_async` placeholder path from CLI module to complete Task 7 architecture cleanup (`services/rentl-cli/src/rentl_cli/main.py:2590`, `services/rentl-cli/src/rentl_cli/main.py:2695`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:105`).
- Align quality benchmark winner assertions to schema contract values `A|B|tie` (not candidate-name labels) so real-LLM runs validate actual compare output semantics (`tests/quality/benchmark/test_benchmark_quality.py:214`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:30`).

### Deferred
- None.
