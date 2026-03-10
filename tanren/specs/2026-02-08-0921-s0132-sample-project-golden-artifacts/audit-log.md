# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): PASS — Sample script and CC0 license satisfy Task 2; SourceLine validation passes (58/58)
- **Task 3** (round 1): FAIL — QA artifact does not satisfy plan requirement for “at least one per QA category”; only four rule labels are represented
- **Task 3** (round 2): FAIL — `qa.jsonl` remains incomplete for category coverage (`other` missing) and still contains non-prefixed violations that prevent strict category mapping
- **Task 2** (round 2): PASS — Task 2 remains compliant; script is valid JSONL, validates as SourceLine (58/58), and includes required structure/content plus CC0 license
- **Task 4** (round 1): PASS — Unit-tier schema validation tests cover script plus all six golden artifact files; `pytest tests/unit/test_golden_artifacts.py` and `make check` both pass
- **Task 5** (round 1): FAIL — Ingest integration test is BDD and fast, but it does not verify full golden-data equality for `line_id`/`text`/`speaker`/`scene_id` across all records
- **Task 5** (round 2): PASS — Ingest integration test now validates full-record equality for `line_id`/`text`/`speaker`/`scene_id` across all lines against `samples/golden/script.jsonl`; `pytest tests/integration/ingest/test_golden_script.py` passes in 0.03s
- **Task 6** (round 1): FAIL — Task updates are applied, but acceptance check fails because `git grep sample_scenes.jsonl` still returns matches in spec documents
- **Task 6** (round 2): PASS — Acceptance is now scoped to operational references and `git grep sample_scenes.jsonl -- ':(exclude)agent-os/specs/'` returns zero matches
- **Task 7** (round 1): FAIL — Full pipeline smoke test fails immediately with `config_error` because test `input_path` resolves outside `workspace_dir` (`Path must stay within workspace`)
- **Task 7** (round 2): FAIL — Task 7 moved the smoke test from integration/FakeLlmRuntime to quality/real-runtime (which was correct per human guidance), but the new test currently fails with `Missing API key environment variable: PRIMARY_KEY` due to not using the same env vars as current passing quality tests.
- **Task 7** (round 3): PASS — Fixed env vars to use RENTL_QUALITY_API_KEY/RENTL_QUALITY_BASE_URL (matching other quality tests), added pytest.mark.skipif for environments without LLM endpoint, and strengthened per-phase assertions. All fix items addressed.
- **Blockers resolved** (2026-02-08): spec.md acceptance criterion updated to reflect quality-layer test (FakeLlmRuntime architecturally infeasible per signposts). Signposts reformatted with machine-readable Status fields. All signposts marked resolved.
- **Demo** (run 1): PASS — All 7 steps passed; full pipeline validation successful
- **Spec Audit** (round 1): FAIL — Performance 5/5, Intent 4/5, Completion 4/5, Security 5/5, Stability 4/5; fix-now 1
- **Task 7** (round 4): PASS — Quality-layer smoke test uses `RENTL_QUALITY_API_KEY`/`RENTL_QUALITY_BASE_URL`, skips cleanly when unset, and retains per-phase + export-schema assertions.
- **Demo** (run 2): PASS — All 7 steps passed; post-audit verification successful
- **Spec Audit** (round 2): PASS — Performance 5/5, Intent 5/5, Completion 5/5, Security 5/5, Stability 5/5; fix-now 0
