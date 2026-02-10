status: fail
fix_now_count: 2

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-10
- Round: 9

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 4/5
- Completion: 4/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — eval-set artifacts contain metadata/hashes only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`), and source text is downloaded at runtime with hash validation (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:13`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:87`).
2. **Apples-to-apples comparison**: **PASS** — compare validates matching line IDs before judging (`services/rentl-cli/src/rentl_cli/main.py:1319`, `services/rentl-cli/src/rentl_cli/main.py:1321`, `packages/rentl-core/src/rentl_core/benchmark/output_loader.py:67`) and uses one judge configuration for all pair tasks (`services/rentl-cli/src/rentl_cli/main.py:1467`, `services/rentl-cli/src/rentl_cli/main.py:1510`).
3. **Scores must include per-line evidence**: **PASS** — per-line reasoning is required in schema (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`) and persisted in report output (`packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:51`).
4. **Benchmark must be runnable standalone**: **PASS** — first-class CLI subcommands exist for both flows (`services/rentl-cli/src/rentl_cli/main.py:1097`, `services/rentl-cli/src/rentl_cli/main.py:1226`) and are executed directly via CLI entrypoints (`services/rentl-cli/src/rentl_cli/main.py:1114`, `services/rentl-cli/src/rentl_cli/main.py:1266`).

## Demo Status
- Latest run: **PASS** (Run 11, 2026-02-10; `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:107`).
- Summary: Step 1 executed; Steps 2-5 were documented as environment-dependent and validated via quality testing (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:108`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:113`).
- Verification gate: **PASS in this audit round** — `make all` completed successfully (Unit 800, Integration 85, Quality 5).

## Standards Adherence
- `testing/three-tier-test-structure`: **PASS** — benchmark coverage exists in all tiers (`tests/unit/benchmark/test_judge.py:1`, `tests/integration/benchmark/test_cli_command.py:1`, `tests/quality/benchmark/test_benchmark_quality.py:1`; standard `agent-os/standards/testing/three-tier-test-structure.md:3`).
- `testing/no-mocks-for-quality-tests`: **PASS** — quality benchmark flow invokes the real compare command path and real judge endpoint when env is configured (`tests/quality/benchmark/test_benchmark_quality.py:134`; standard `agent-os/standards/testing/no-mocks-for-quality-tests.md:41`).
- `testing/bdd-for-integration-quality`: **PASS** — integration and quality suites are feature-backed Given/When/Then (`tests/features/benchmark/cli_command.feature:1`, `tests/quality/features/benchmark/benchmark_quality.feature:1`; standard `agent-os/standards/testing/bdd-for-integration-quality.md:3`).
- `python/pydantic-only-schemas`: **PASS** — benchmark schema contracts are Pydantic models (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`; standard `agent-os/standards/python/pydantic-only-schemas.md:3`).
- `python/async-first-design`: **PASS** — CLI entrypoints bridge to async implementations immediately and compare uses structured concurrency (`services/rentl-cli/src/rentl_cli/main.py:1114`, `services/rentl-cli/src/rentl_cli/main.py:1266`, `services/rentl-cli/src/rentl_cli/main.py:1539`; standard `agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — benchmark schema fields are explicitly typed with `Field(..., description=...)` (`packages/rentl-schemas/src/rentl_schemas/benchmark/config.py:62`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`; standard `agent-os/standards/python/strict-typing-enforcement.md:32`).
- `ux/trust-through-transparency`: **violation (Medium)** — override-mode OpenRouter path crashes with a Python local-variable error instead of actionable user guidance (`services/rentl-cli/src/rentl_cli/main.py:1461`, repro output: `Unexpected error: cannot access local variable 'config' where it is not associated with a value`; standard `agent-os/standards/ux/trust-through-transparency.md:67`, `agent-os/standards/ux/trust-through-transparency.md:73`).
- `testing/validate-generated-artifacts`: **PASS** — compare report artifacts are schema-validated in integration and quality tests (`tests/integration/benchmark/test_cli_command.py:443`, `tests/quality/benchmark/test_benchmark_quality.py:165`; standard `agent-os/standards/testing/validate-generated-artifacts.md:7`).

## Regression Check
- Regression detected in Task 10 override-mode area that previously failed for config coupling: OpenRouter override now fails at runtime due `config` dereference outside config mode (`services/rentl-cli/src/rentl_cli/main.py:1461`), despite prior Task 10 fixes tracked in `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit-log.md:70`.
- Resolved Task 11 signpost remains implemented (judge now uses pydantic-ai `Agent` with `output_type`) (`packages/rentl-core/src/rentl_core/benchmark/judge.py:13`, `packages/rentl-core/src/rentl_core/benchmark/judge.py:186`).
- Benchmark-focused test suites are currently green (`uv run pytest -q tests/unit/benchmark tests/integration/benchmark` → 108 passed).

## Action Items

### Fix Now
- Override-mode OpenRouter compare path crashes because `config` is referenced outside config-based branch (`services/rentl-cli/src/rentl_cli/main.py:1461`). Repro: `RENTL_OPENROUTER_API_KEY=dummy uv run rentl benchmark compare <a.jsonl> <b.jsonl> --judge-base-url https://openrouter.ai/api/v1 --judge-model test-model --judge-api-key-env RENTL_OPENROUTER_API_KEY`.
- Add integration BDD regression coverage for OpenRouter override mode and `openrouter_provider.require_parameters` propagation (`tests/integration/benchmark/test_cli_command.py`, `tests/features/benchmark/cli_command.feature`).

### Deferred
- None.
