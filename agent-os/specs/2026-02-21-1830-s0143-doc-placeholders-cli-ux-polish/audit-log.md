# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): FAIL — Replaced placeholders now point to a nonexistent spec path, so orchestrator examples are not copy-pasteable.
- **Task 3** (round 1): FAIL — Task was checked off without full implementation: `version` docstring lacks required `\f` gate, and required help-output verification is currently blocked by `ModuleNotFoundError: No module named 'griffe'`.
- **Task 2** (round 2): PASS — Placeholder cleanup and stale-reference fixes are implemented; orchestrator examples now use a real spec path.
- **Task 4** (round 1): FAIL — Extracted core `migrate`/`check-secrets` handlers crash with uncaught `AttributeError` on malformed TOML shapes instead of graceful validation flow.
- **Task 4** (round 2): PASS — Malformed TOML-shape guards are implemented with regression tests, and extracted core handlers now fail gracefully without uncaught `AttributeError`.
- **Task 5** (round 1): FAIL — `init` validates config only after writing `rentl.toml`, so invalid input can leave a broken config file and bypass `ConfigValidationError` handling.
- **Task 5** (round 2): FAIL — Pre-write `ConfigValidationError` from `generate_project` still maps to `runtime_error` (exit 99) in `rentl init` instead of `validation_error` (exit 11).
- **Task 4** (round 3): PASS — Thin-adapter extraction remains compliant; core migration/secret checks and CLI serialization/auto-migrate regression tests pass.
- **Task 6** (round 1): FAIL — Task requires ingest/export milestone progress tests, but only ingest milestone assertions were added.
- **Task 6** (round 2): PASS — Export milestone regression coverage is implemented and verified; `PHASE_PROGRESS` asserts both "Selected ... lines for export" and "Wrote ... lines".
- **Task 7** (round 1): PASS — Final integration fixes are valid; help registry and init-prompt test updates pass targeted tests and full `make all` gate.
- **Demo** (run 1): PASS — All 7 [RUN] steps passed: no doc placeholders, canonical env vars, full help registry, \f gates working, zero CLI imports in core, init preview + validation working, make all green (7 run, 7 verified)
