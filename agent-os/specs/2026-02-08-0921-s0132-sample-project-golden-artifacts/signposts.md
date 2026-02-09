# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---

- **Task:** Task 3 (Generate Golden Artifacts)
- **Status:** resolved
- **Problem:** Task 3 requires `qa.jsonl` to include sample violations "at least one per QA category", but the produced artifact stores only free-text `rule_violated` labels and currently covers only four labels.
- **Evidence:** `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:35`; `packages/rentl-schemas/src/rentl_schemas/primitives.py:155` defines 8 QA categories (`grammar`, `terminology`, `style`, `consistency`, `formatting`, `context`, `cultural`, `other`); `samples/golden/artifacts/qa.jsonl:1`..`samples/golden/artifacts/qa.jsonl:4` contains only `Onomatopoeia formatting`, `Onomatopoeia consistency`, `Sentence completeness`, `Honorific consistency`.
- **Resolution:** Fixed via audit round 1 fix items — all 8 QA categories represented with `<Category>: <rule>` prefix convention.
- **Impact:** Future tasks/tests that expect category-level QA coverage cannot verify completeness from current golden QA data; this blocks deterministic checks tied to category coverage.

- **Task:** Task 3 (Generate Golden Artifacts)
- **Status:** resolved
- **Problem:** The follow-up Task 3 fix still misses `other` coverage and leaves non-prefixed `rule_violated` entries, so category coverage cannot be strictly derived from a single convention.
- **Evidence:** `packages/rentl-schemas/src/rentl_schemas/primitives.py:155` includes `OTHER`; `samples/golden/artifacts/qa.jsonl:1` uses `Onomatopoeia formatting` and `Onomatopoeia consistency` (no `<Category>:` prefix), and `samples/golden/artifacts/qa.jsonl:1`..`samples/golden/artifacts/qa.jsonl:4` contain no `Other:` violation; `samples/golden/artifacts/README.md:22` defines the required `<Category>: <specific rule>` convention.
- **Resolution:** Fixed via audit round 2 fix items — added `Other:` violation and converted all entries to `<Category>: <rule>` format.
- **Impact:** Any deterministic check for "all QA categories represented" remains brittle and can silently pass/fail depending on ad-hoc inference rules rather than explicit category labels.

- **Task:** Task 5 (Ingest Integration Test)
- **Status:** resolved
- **Problem:** The ingest BDD test uses spot checks and pattern checks instead of verifying full record equality with the golden script, so regressions in later rows can pass undetected.
- **Evidence:** Plan contract requires matching golden data for `line_ids`, `text`, `speakers`, and `scenes` (`agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:57`), but assertions only sample the first IDs (`tests/integration/ingest/test_golden_script.py:77`), first text line (`tests/integration/ingest/test_golden_script.py:103`), selected speakers (`tests/integration/ingest/test_golden_script.py:119`), and scene-count heuristics (`tests/integration/ingest/test_golden_script.py:143`).
- **Resolution:** Fixed via audit round 1 fix item — replaced sampled assertions with full-record equality checks.
- **Impact:** Adapter regressions that alter ordering or values outside sampled rows can still pass Task 5, weakening confidence in ingest correctness before Task 7 pipeline smoke coverage.

- **Task:** Task 6 (Replace sample_scenes.jsonl)
- **Status:** resolved
- **Problem:** Task 6 acceptance uses a repo-wide literal grep (`git grep sample_scenes.jsonl`) that fails on intentional historical references in spec artifacts, even though operational references were replaced.
- **Evidence:** Current grep still matches `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/demo.md:17`, `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:9`, `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/plan.md:69`, and `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/spec.md:9`.
- **Resolution:** Fixed via audit round 1 fix item — scoped grep to exclude spec docs: `git grep sample_scenes.jsonl -- ':(exclude)agent-os/specs/'`.
- **Impact:** Future auditors can repeatedly fail Task 6 despite correct code/config updates unless acceptance criteria are scoped to operational files or historical mentions are excluded by rule.

- **Task:** Task 7 (Full Pipeline Smoke Test)
- **Status:** resolved
- **Problem:** The new integration test builds a config where `input_path` points outside `workspace_dir`, which violates CLI path-sandboxing and fails before any pipeline phase runs.
- **Evidence:** `tests/integration/pipeline/test_golden_script_pipeline.py:157` sets `workspace_dir = tmp_path / "workspace"` and `tests/integration/pipeline/test_golden_script_pipeline.py:161` sets `script_copy = tmp_path / "script.jsonl"`; running `pytest -q tests/integration/pipeline/test_golden_script_pipeline.py` fails at `tests/integration/pipeline/test_golden_script_pipeline.py:197` with `config_error` message `Path must stay within workspace: /tmp/.../script.jsonl` from `services/rentl-cli/src/rentl_cli/main.py:1398`.
- **Resolution:** do-task round 2 — changed line 161 to `script_copy = ctx.workspace_dir / "script.jsonl"` to place the script inside the workspace directory.
- **Files affected:** `tests/integration/pipeline/test_golden_script_pipeline.py`

- **Task:** Task 7 (Full Pipeline Smoke Test)
- **Status:** resolved
- **Problem:** FakeLlmRuntime monkeypatch does not intercept agent HTTP calls; agents use pydantic-ai which makes direct HTTP requests to configured base_url, bypassing the CLI's `_build_llm_runtime()`.
- **Evidence:** Test fails with `Connection error` after fixing path issue; log shows `"message":"Retrying after error: Connection error."` and `"Agent execution failed: Connection error."` at `tests/integration/pipeline/test_golden_script_pipeline.py` when running context phase with scene_summarizer agent. Agents are created via `build_agent_pools` in `packages/rentl-agents/src/rentl_agents/wiring.py:1108` which does not accept an injectable runtime parameter. The `OpenAICompatibleRuntime` in `packages/rentl-llm/src/rentl_llm/openai_runtime.py:27` creates `OpenAIProvider` instances that make real HTTP calls to `base_url=http://localhost:8001/v1` configured in test.
- **Resolution:** do-task — moved test from integration to quality layer. Quality tests use real HTTP endpoints per layer rules (no mocking allowed), which aligns with the test's requirements. Created `tests/quality/pipeline/test_golden_script_pipeline.py` and `tests/quality/features/pipeline/golden_script_pipeline.feature`, removed FakeLlmRuntime monkeypatch step, deleted integration test files. Updated plan.md to reflect test is now in quality layer with <30s timeout instead of <5s.
- **Files affected:** Created `tests/quality/pipeline/test_golden_script_pipeline.py`, `tests/quality/features/pipeline/golden_script_pipeline.feature`, `tests/quality/pipeline/__init__.py`, `tests/quality/conftest.py`; deleted `tests/integration/pipeline/test_golden_script_pipeline.py`, `tests/integration/features/pipeline/golden_script_pipeline.feature`

- **Task:** Task 7 (Full Pipeline Smoke Test)
- **Status:** resolved
- **Problem:** Integration-layer full pipeline testing with FakeLlmRuntime is architecturally infeasible: agents make direct HTTP calls via pydantic-ai's `OpenAIProvider` which bypasses CLI runtime injection. The monkeypatch on `cli_main._build_llm_runtime` at `tests/integration/conftest.py:149` cannot intercept agent HTTP calls to configured `base_url`.
- **Evidence:** Spec requires integration test with FakeLlmRuntime at `agent-os/specs/2026-02-08-0921-s0132-sample-project-golden-artifacts/spec.md:35`; agents created via `build_agent_pools` at `packages/rentl-agents/src/rentl_agents/wiring.py:1108` do not accept injectable runtime parameter; `OpenAICompatibleRuntime` at `packages/rentl-llm/src/rentl_llm/openai_runtime.py:27` creates `OpenAIProvider` instances that make real HTTP calls to configured endpoint. Previous integration test attempt at `tests/integration/pipeline/test_golden_script_pipeline.py` failed with `Connection error` after FakeLlmRuntime monkeypatch.
- **Resolution:** user via resolve-blockers 2026-02-08 — Accepted quality-layer test at `tests/quality/pipeline/test_golden_script_pipeline.py:1` as the correct approach. Test uses RENTL_QUALITY_API_KEY and RENTL_QUALITY_BASE_URL environment variables (matching other quality tests) with pytest.mark.skipif to skip gracefully when environment is not configured. Integration-layer pipeline coverage deferred until runtime injection architecture is implemented.
- **Impact:** Integration-layer pipeline coverage requires runtime injection architecture (agents accepting injectable runtime parameter, or HTTP interception layer). Quality test provides smoke coverage using real endpoints. Test skips cleanly in environments without LLM endpoint access.
- **Files affected:** `tests/quality/pipeline/test_golden_script_pipeline.py`, `tests/quality/conftest.py`
