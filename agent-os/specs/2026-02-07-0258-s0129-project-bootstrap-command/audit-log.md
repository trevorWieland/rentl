# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): FAIL — Missing test coverage for the new `build_agent_pools()` fallback branch when `RunConfig.agents` is `None`.
- **Task 2** (round 2): PASS — Optional `[agents]` behavior is implemented end-to-end and validated by schema, CLI resolution, and wiring fallback tests.
- **Task 3** (round 1): FAIL — `InitAnswers` allows unsupported `input_format` values (for example `tsv`) that generate `rentl.toml` failing `RunConfig` validation.
- **Task 3** (round 2): PASS — `input_format` is now constrained to `FileFormat`, seed generation aligns with supported formats, and regression coverage rejects unsupported values.
- **Task 4** (round 1): FAIL — `rentl init` cancellation is routed into error handling (crashing with `ErrorResponse` validation) and required CLI tests were not added.
- **Task 4** (round 2): FAIL — `rentl init` accepts trailing-comma target languages and reports success while generating `rentl.toml` that fails `validate_run_config()`.
- **Task 4** (round 3): PASS — Target-language sanitization now prevents invalid blank entries and regression tests verify accepted inputs generate validating config.
- **Task 5** (round 1): PASS — Added BDD integration coverage for init project bootstrap and fixed seed-data schema compatibility; generated project validates and resolves cleanly.
- **Demo** (run 1): FAIL — Generated config uses invalid agent names, causing runtime failure despite passing schema validation. Task 6 added to fix agent name mapping.
- **Task 6** (round 1): FAIL — New integration agent-pool assertion depends on `OPENROUTER_API_KEY` from the external environment, so the scenario fails in a clean test run.
- **Task 6** (round 2): FAIL — New env-var scoping regression test is itself environment-dependent and fails when `OPENROUTER_API_KEY` is already set in the shell.
- **Task 6** (round 3): PASS — Env-var scoping regression now uses an isolated `monkeypatch.context()` and verifies API key restoration deterministically across pre-existing environment states.
- **Demo** (run 2): FAIL — Generated config missing required ingest/export phases, causing "Source lines are required" error at runtime. Task 7 added to fix pipeline phase generation.
- **Task 7** (round 1): FAIL — Config generation now includes ingest/export phases, but integration coverage still stops at `build_agent_pools()` and does not verify full pipeline execution through export.
