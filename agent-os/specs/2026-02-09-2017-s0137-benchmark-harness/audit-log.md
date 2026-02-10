# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): PASS — Benchmark schema module, rubric/report models, and unit validation/round-trip coverage align with plan and standards.
- **Task 3** (round 1): FAIL — Eval-set task marked complete prematurely; committed manifest/slice artifacts and parse-flow coverage are missing, and default parser IDs fail schema validation on KSRE-style filenames.
- **Task 3** (round 2): FAIL — Parser ID normalization fix is verified, but manifest hashes are invalid placeholders and the configured demo slice does not meet required mixed-content coverage.
- **Task 2** (round 2): PASS — Task 2 schema contract remains satisfied in current tree; strict typed Pydantic models and benchmark schema tests still pass (32/32).
- **Task 4** (round 1): FAIL — Integration test uses direct pytest assertions instead of required BDD Given/When/Then structure for integration tier scenarios.
- **Task 4** (round 2): FAIL — BDD conversion is present but broken: async `When` step is never awaited, so integration scenarios do not execute and required prompt/result assertions fail.
- **Task 4** (round 3): FAIL — Metadata assertions in Task 4 unit/integration tests are partially no-op because expected-value checks were accidentally placed inside comments after `# type: ignore`.
- **Task 4** (round 4): PASS — Metadata assertions now enforce exact `mtl_baseline`/`model` values in unit and BDD integration tests, and targeted Task 4 suites pass (8/8).
- **Task 5** (round 1): FAIL — Judge integration BDD steps are unbound (`StepDefinitionNotFoundError`), and Task 5 test coverage misses randomized head-to-head remapping/per-dimension winner guarantees.
- **Task 4** (round 5): PASS — Re-audit confirms Task 4 implementation and BDD/unit coverage remain compliant; `pytest -q tests/unit/benchmark/test_mtl_baseline.py tests/integration/benchmark/test_mtl_baseline_flow.py` passes (8/8).
- **Task 5** (round 2): PASS — Task 5 fix items are implemented (BDD table steps bind, randomized head-to-head remapping is covered, per-dimension winners are enforced), and `pytest -q tests/unit/benchmark/test_judge.py tests/integration/benchmark/test_judge_flow.py` passes (23/23).
- **Task 8** (round 1): FAIL — Task was marked complete after adding unit report tests only; required benchmark CLI integration/quality coverage is missing, and new assertions codify a known head-to-head winner-mapping defect.
- **Task 7** (round 1): FAIL — Benchmark CLI remains placeholder-based (MTL reused as rentl), scoring-mode/reference handling is not implemented end-to-end, and report head-to-head winner aggregation compares incompatible label types.
- **Task 6** (round 1): PASS — `BenchmarkReportBuilder` and `format_report_summary` satisfy Task 6 scope (dimension aggregates, head-to-head rates, report assembly/serialization path, and unit coverage); `pytest -q tests/unit/benchmark/test_report_generation.py` passes (12/12).
- **Task 7** (round 2): FAIL — Winner-slot aggregation fix is verified, but scoring-mode still violates CLI/report contract (hyphenated values rejected and fallback can report `reference_based` while using no references).
- **Task 6** (round 2): PASS — Re-audit confirms Task 6 report generation contract remains satisfied (aggregation, head-to-head summary, report formatting, and JSON serialization path); resolved winner-slot mapping signpost behavior is verified in code/tests.
- **Task 7** (round 3): PASS — Verified fallback metadata fix: when reference-based mode falls back, `actual_scoring_mode` is set to `reference_free` before report generation (`services/rentl-cli/src/rentl_cli/main.py:2454`, `services/rentl-cli/src/rentl_cli/main.py:2515`).
- **Task 8** (round 2): FAIL — Benchmark CLI integration BDD coverage is broken at collection time because `test_cli_command.py` references a non-existent feature path (`FileNotFoundError`), so Task 8 cannot remain checked off.
- **Task 7** (round 4): FAIL — Benchmark CLI still uses placeholder pipeline wiring (`rentl_translations = mtl_translations`), so the task contract to run the real rentl pipeline is not met.
- **Task 3** (round 3): PASS — Eval-set downloader/parser artifacts and contracts remain valid; resolved hash and slice signposts are verified in code, and Task 3 suites pass (`34/34`).
- **Task 4** (round 6): FAIL — Output loader work is correct, but Task 4 still leaves regressions: stale CLI integration mocks reference deleted `MTLBaselineGenerator`, dead placeholder benchmark code remains, and judge API removals broke integration BDD scenarios.

---

**Architecture revision** (resolve-blockers, 2026-02-10): spec.md, plan.md, demo.md, signposts.md rewritten. Original design embedded pipeline execution inside benchmark command and hardcoded JP→EN 2-system comparison. Revised to: benchmark is a pure comparison tool taking 2+ rentl run output files, head-to-head only (no isolated scoring), N-way all-pairs with Elo, language-agnostic. MTL baseline is just a translate-only rentl run. Tasks 1+3 remain done; Tasks 2/4/5/6/7/8 require rework under new plan. Old Task 4 (MTL baseline generator) replaced with output loader + dead code removal.
