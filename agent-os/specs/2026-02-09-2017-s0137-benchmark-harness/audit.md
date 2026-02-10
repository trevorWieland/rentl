status: fail
fix_now_count: 3

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-10
- Round: 2

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 4/5
- Completion: 3/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — eval content is downloaded at runtime from KSRE (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:33`) and committed eval-set artifacts are manifest/slices only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`; command output `rg --files | rg '\\.rpy$|katawa|ksre|script-a1'` shows no committed `.rpy` source files).
2. **Apples-to-apples comparison**: **PASS** — compare enforces matching line IDs before judging (`services/rentl-cli/src/rentl_cli/main.py:1313`, `services/rentl-cli/src/rentl_cli/main.py:1316`) and uses one judge/runtime config across all pairings in a run (`services/rentl-cli/src/rentl_cli/main.py:1329`, `services/rentl-cli/src/rentl_cli/main.py:1356`).
3. **Scores must include per-line evidence**: **PASS** — per-line reasoning is required in schema (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`), enforced in judge response parsing (`packages/rentl-core/src/rentl_core/benchmark/judge.py:129`), and emitted in report line results (`services/rentl-cli/src/rentl_cli/main.py:1455`).
4. **Benchmark runnable standalone**: **PASS** — first-class CLI subcommands exist for `rentl benchmark download` and `rentl benchmark compare` (`services/rentl-cli/src/rentl_cli/main.py:1099`, `services/rentl-cli/src/rentl_cli/main.py:1229`).

## Demo Status
- Latest run: **PASS** (Run 3, 2026-02-10)
- `demo.md` records Step 1 passing and Steps 2-5 intentionally skipped with rationale (external API/runtime constraints) (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:40`).

## Standards Adherence
- `testing/three-tier-test-structure`: **PASS** — benchmark tests are in unit/integration/quality tiers (`tests/unit/benchmark/test_output_loader.py:1`, `tests/integration/benchmark/test_cli_command.py:1`, `tests/quality/benchmark/test_benchmark_quality.py:1`).
- `testing/no-mocks-for-quality-tests`: **PASS** — quality scenario invokes real CLI compare path and does not mock judge runtime (`tests/quality/benchmark/test_benchmark_quality.py:134`).
- `testing/bdd-for-integration-quality`: **PASS** — integration and quality suites use BDD scenarios and Given/When/Then steps (`tests/integration/benchmark/test_cli_command.py:20`, `tests/quality/benchmark/test_benchmark_quality.py:34`, `agent-os/standards/testing/bdd-for-integration-quality.md:3`).
- `python/pydantic-only-schemas`: **PASS** — benchmark contracts are Pydantic models (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`, `agent-os/standards/python/pydantic-only-schemas.md:3`).
- `python/async-first-design`: **PASS** — compare uses structured concurrency for judge calls (`services/rentl-cli/src/rentl_cli/main.py:1420`, `agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — schema fields are explicitly typed and defined with `Field` descriptions (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`, `packages/rentl-schemas/src/rentl_schemas/benchmark/config.py:62`, `agent-os/standards/python/strict-typing-enforcement.md:32`).
- `ux/trust-through-transparency`: **violation (Medium)** — progress uses task index (`completed=index + 1`) instead of completed-count, causing non-monotonic/inaccurate progress under out-of-order completion (`services/rentl-cli/src/rentl_cli/main.py:1417`; repro output `updates [2, 3, 1]`, final `1`; standard requires explainable progress updates `agent-os/standards/ux/trust-through-transparency.md:69`).
- `testing/validate-generated-artifacts`: **PASS** — generated compare report is validated against `BenchmarkReport` schema in quality flow (`tests/quality/benchmark/test_benchmark_quality.py:169`, `agent-os/standards/testing/validate-generated-artifacts.md:10`).

## Regression Check
- The unresolved progress-accounting issue remains and matches the existing unresolved signpost (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:114`) and prior task-audit finding (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:48`).
- Legacy pre-revision benchmark path still exists as dead placeholder (`services/rentl-cli/src/rentl_cli/main.py:2590`, `services/rentl-cli/src/rentl_cli/main.py:2695`), so prior cleanup expectation remains unmet (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:132`).
- New quality-test contract drift identified: the quality assertion expects candidate-name winners while schema/judge emit `A|B|tie` (`tests/quality/benchmark/test_benchmark_quality.py:214`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:34`).

## Action Items

### Fix Now
- Fix benchmark compare progress accounting to use completed-task count (monotonic) rather than task index and prevent regressions under out-of-order completion (`services/rentl-cli/src/rentl_cli/main.py:1417`; `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/signposts.md:114`).
- Remove stale `_run_benchmark_async` monolithic placeholder path from the current CLI module (`services/rentl-cli/src/rentl_cli/main.py:2590`, `services/rentl-cli/src/rentl_cli/main.py:2695`; contract reference `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:105`).
- Correct quality BDD winner assertions to match `HeadToHeadResult` winner labels (`A|B|tie`) so real-LLM quality runs validate the actual schema contract (`tests/quality/benchmark/test_benchmark_quality.py:214`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:30`).

### Deferred
- None.
