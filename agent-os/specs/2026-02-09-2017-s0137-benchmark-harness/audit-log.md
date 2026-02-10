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
