status: fail
fix_now_count: 1

# Audit: s0.1.37 Benchmark Harness v0.1

- Spec: s0.1.37
- Issue: https://github.com/trevorWieland/rentl/issues/37
- Date: 2026-02-11
- Round: 11

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 4/5
- Completion: 3/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. **No committed copyrighted text**: **PASS** — benchmark eval-set artifacts are hash/config metadata only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:1`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/slices.json:1`) and raw scripts are downloaded + hash-validated at runtime (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:33`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:87`).
2. **Apples-to-apples comparison**: **PASS** — compare validates matching line IDs before judging (`packages/rentl-core/src/rentl_core/benchmark/output_loader.py:67`, `services/rentl-cli/src/rentl_cli/main.py:1329`) and runs all pairwise lines through a single judge configuration for that run (`services/rentl-cli/src/rentl_cli/main.py:1474`, `services/rentl-cli/src/rentl_cli/main.py:1517`).
3. **Scores must include per-line evidence**: **PASS** — per-line reasoning is part of the result schema (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:33`) and integration/quality checks assert reasoning is present (`tests/integration/benchmark/test_cli_command.py:499`, `tests/quality/benchmark/test_benchmark_quality.py:191`).
4. **Benchmark must be runnable standalone**: **PASS** — first-class CLI subcommands are registered and bridge directly to async implementations (`services/rentl-cli/src/rentl_cli/main.py:1097`, `services/rentl-cli/src/rentl_cli/main.py:1114`, `services/rentl-cli/src/rentl_cli/main.py:1226`, `services/rentl-cli/src/rentl_cli/main.py:1266`).

## Demo Status
- Latest run: **PASS** (Run 13, 2026-02-10; `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:123`).
- Summary: demo still records Step 1 pass with Steps 2-5 environment-gated (`agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:124`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/demo.md:129`).
- Additional audit evidence: full gate in this environment is green (`make lint-check`, `make type`, `make unit`, `make integration`, `make quality`), but real-LLM benchmark quality run fails when executed (`set -a; source .env; set +a; uv run pytest -q tests/quality/benchmark/test_benchmark_quality.py`).

## Standards Adherence
- `testing/three-tier-test-structure`: **PASS** — benchmark coverage exists in unit/integration/quality tiers (`tests/unit/benchmark/test_judge.py:1`, `tests/integration/benchmark/test_cli_command.py:1`, `tests/quality/benchmark/test_benchmark_quality.py:1`; rule `agent-os/standards/testing/three-tier-test-structure.md:3`).
- `testing/no-mocks-for-quality-tests`: **PASS** — quality benchmark scenario uses real CLI/judge path and no mocked LLM (`tests/quality/benchmark/test_benchmark_quality.py:134`; rule `agent-os/standards/testing/no-mocks-for-quality-tests.md:41`).
- `testing/bdd-for-integration-quality`: **PASS** — integration and quality flows are feature-backed Given/When/Then tests (`tests/features/benchmark/cli_command.feature:1`, `tests/quality/features/benchmark/benchmark_quality.feature:1`; rule `agent-os/standards/testing/bdd-for-integration-quality.md:3`).
- `python/pydantic-only-schemas`: **PASS** — benchmark contracts are Pydantic models (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:17`, `packages/rentl-schemas/src/rentl_schemas/benchmark/report.py:39`; rule `agent-os/standards/python/pydantic-only-schemas.md:3`).
- `python/async-first-design`: **PASS** — CLI entrypoints bridge immediately to async and compare executes concurrent work (`services/rentl-cli/src/rentl_cli/main.py:1114`, `services/rentl-cli/src/rentl_cli/main.py:1266`, `services/rentl-cli/src/rentl_cli/main.py:1546`; rule `agent-os/standards/python/async-first-design.md:39`).
- `python/strict-typing-enforcement`: **PASS** — benchmark schemas use explicit typed `Field` definitions (`packages/rentl-schemas/src/rentl_schemas/benchmark/config.py:62`, `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:30`; rule `agent-os/standards/python/strict-typing-enforcement.md:32`).
- `ux/trust-through-transparency`: **violation (Medium)** — on real-LLM quality execution failure, compare emits only `Unexpected error: not enough values to unpack...` (`services/rentl-cli/src/rentl_cli/main.py:1602`), which does not provide actionable recovery context expected by the standard (`agent-os/standards/ux/trust-through-transparency.md:72`).
- `testing/validate-generated-artifacts`: **PASS** — integration/quality tests validate output via `BenchmarkReport.model_validate(...)` (`tests/integration/benchmark/test_cli_command.py:446`, `tests/quality/benchmark/test_benchmark_quality.py:165`; rule `agent-os/standards/testing/validate-generated-artifacts.md:7`).

## Regression Check
- Previously fixed OpenRouter override-mode crash remains resolved (`services/rentl-cli/src/rentl_cli/main.py:1468`) with regression BDD coverage still present (`tests/features/benchmark/cli_command.feature:50`, `tests/integration/benchmark/test_cli_command.py:650`).
- Previously fixed async progress monotonicity remains covered (`tests/features/benchmark/cli_command.feature:20`, `tests/integration/benchmark/test_cli_command.py:343`).
- New regression detected: real-LLM quality benchmark path fails under current project OpenRouter config because `tests/quality/benchmark/test_benchmark_quality.py:152` passes `gpt-4o-mini`, and compare exits with `Unexpected error: not enough values to unpack` (`services/rentl-cli/src/rentl_cli/main.py:1602`). Repro: `set -a; source .env; set +a; uv run pytest -q tests/quality/benchmark/test_benchmark_quality.py`.

## Action Items

### Fix Now
- Make the real-LLM benchmark quality scenario pass with project OpenRouter config by using an OpenRouter-compatible judge model identifier (provider-qualified or config-derived) and ensuring compare does not fail with `Unexpected error: not enough values to unpack` (`tests/quality/benchmark/test_benchmark_quality.py:152`, `services/rentl-cli/src/rentl_cli/main.py:1602`).

### Deferred
- None.
