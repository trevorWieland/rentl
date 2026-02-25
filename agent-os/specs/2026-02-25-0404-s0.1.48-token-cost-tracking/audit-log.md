# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): PASS — Schema updates and unit tests satisfy Task 2 requirements with no issues found.
- **Task 3** (round 1): PASS — Aggregation now includes completed/failed/retry usage with waste ratio and passing unit coverage for mixed and edge cases.

- **Task 4** (round 1): PASS — Cost overrides are wired end-to-end with runtime telemetry propagation; OpenRouter cost propagation constraint documented in signpost and verified against pydantic-ai usage mapping.
- **Task 5** (round 1): PASS — Run report data now includes total/phase cost, waste ratio, and failed/retried token segments, and persists to JSON report artifacts.
- **Task 6** (round 1): FAIL — New status-cost integration tests fail validation (`phase_status` does not match `phase_progress.status`), and non-JSON status display assertions are missing.
- **Task 6** (round 2): PASS — Resolved fixture status mismatch and added non-JSON display assertions for `cost` (including `N/A`) and `waste`; verified with `pytest -q tests/integration/cli/test_status_cost.py` (4 passed).
- **Demo** (run 1): PASS — All 4 [RUN] steps passed: make all (1121 unit + 103 integration), qwen3 pilot (322 lines, cost null), deepseek pilot (322 lines, cost $0.046), status display verified (4 run, 4 verified)
- **Spec Audit** (round 1): PASS — Performance 5/5, Intent 5/5, Completion 5/5, Security 5/5, Stability 5/5; fix-now count 0.
- **Task 8** (round 1): FAIL — `deepseek-mtl-pilot.toml` pricing overrides (`0.30/0.88`) do not match current OpenRouter DeepSeek V3.2 pricing (`0.25/0.40`), so Task 8 pricing verification is incomplete.
- **Demo** (run 2): PASS — All 4 [RUN] steps passed post-Task 9: make check (1132 unit + 103 integration), qwen3 pilot (322 lines, cost null, cache/reasoning fields present), deepseek pilot (322 lines, cost $0.0337, cache_read_tokens 101632), status display verified (4 run, 4 verified)
- **Spec Audit** (round 2): FAIL — Performance 5/5, Intent 4/5, Completion 4/5, Security 5/5, Stability 4/5; fix-now count 1 (status retry/failure aggregation undercount in `rentl_core.status`).
- **Task 9** (round 1): FAIL — Task 9 commit updated report serialization/tests but did not implement schema/runtime/status cache+reasoning fields; targeted Task 9 tests fail with missing `AgentUsageTotals` attributes.
- **Task 9** (round 2): PASS — Schema and runtime now map cache/reasoning tokens (`progress.py`, `_build_usage_totals`), with targeted unit and integration tests passing.
- **Demo** (run 3): PASS — All 4 [RUN] steps passed post-audit fixes: make all (1133 unit + 103 integration), qwen3 pilot (322 lines, cost null, cache/reasoning fields present), deepseek pilot (322 lines, cost $0.0337, cache_read_tokens 112576), status display verified (4 run, 4 verified)
