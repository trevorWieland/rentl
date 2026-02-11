status: fail
fix_now_count: 1

# Audit: s0.1.22 Functional Onboarding

- Spec: s0.1.22
- Issue: https://github.com/trevorWieland/rentl/issues/23
- Date: 2026-02-11
- Round: 1

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 5/5
- Completion: 4/5
- Security: 5/5
- Stability: 4/5

## Non-Negotiable Compliance
1. Init output must be immediately runnable: **PASS** — full onboarding flow (`init -> doctor -> run-pipeline -> export`) passes with no manual edits in `tests/integration/cli/test_onboarding_e2e.py:333` and `tests/integration/cli/test_onboarding_e2e.py:417`; demo run confirms end-to-end success in `agent-os/specs/2026-02-11-1011-s0122-functional-onboarding/demo.md:97`.
2. No silent failures during first run: **PASS** — command handlers emit structured errors (no swallowed exceptions/tracebacks) via `_error_response` and non-zero exits in `services/rentl-cli/src/rentl_cli/main.py:985`, `services/rentl-cli/src/rentl_cli/main.py:1004`, `services/rentl-cli/src/rentl_cli/main.py:877`, and doctor surfaces fix suggestions in `packages/rentl-core/src/rentl_core/doctor.py:332` and `packages/rentl-core/src/rentl_core/doctor.py:394`.
3. Doctor must catch all first-run blockers: **PASS** — generated onboarding project passes doctor + pipeline in latest demo (`agent-os/specs/2026-02-11-1011-s0122-functional-onboarding/demo.md:99`, `agent-os/specs/2026-02-11-1011-s0122-functional-onboarding/demo.md:100`).
4. Init-generated config must round-trip validate: **PASS** — generated TOML is validated against `RunConfig` in `tests/unit/core/test_init.py:100` and `tests/integration/cli/test_init.py:117`.

## Demo Status
- Latest run: PASS (Run 3, 2026-02-11)
- Demo evidence in `agent-os/specs/2026-02-11-1011-s0122-functional-onboarding/demo.md:97` through `agent-os/specs/2026-02-11-1011-s0122-functional-onboarding/demo.md:121` shows all 6 steps passing.

## Standards Adherence
- `ux/frictionless-by-default`: PASS — init has presets + guided prompts (`services/rentl-cli/src/rentl_cli/main.py:570`) and README quickstart exists (`README.md:42`).
- `ux/trust-through-transparency`: PASS — doctor/run commands provide explicit status and errors (`services/rentl-cli/src/rentl_cli/main.py:361`, `services/rentl-cli/src/rentl_cli/main.py:1001`).
- `ux/progress-is-product`: PASS — run summary includes status/log/progress/report metadata and next steps (`services/rentl-cli/src/rentl_cli/main.py:2502`, `services/rentl-cli/src/rentl_cli/main.py:2526`).
- `architecture/thin-adapter-pattern`: PASS — CLI delegates diagnostics/project generation to core (`services/rentl-cli/src/rentl_cli/main.py:359`, `services/rentl-cli/src/rentl_cli/main.py:658`).
- `architecture/config-path-resolution`: **VIOLATION (High)** — doctor workspace checks are evaluated from unresolved config strings (`packages/rentl-core/src/rentl_core/doctor.py:262`) loaded via `run_doctor()` (`packages/rentl-core/src/rentl_core/doctor.py:450`) instead of resolving relative to `config_path.parent`; repro command showed false pass (`workspace_status pass`) while config-dir `out/` and `logs/` were absent.
- `architecture/api-response-format`: PASS — JSON command responses use `{data,error,meta}` envelope (`services/rentl-cli/src/rentl_cli/main.py:833`, `services/rentl-cli/src/rentl_cli/main.py:982`).
- `architecture/openrouter-provider-routing`: PASS — OpenRouter endpoints default to `require_parameters=True` in schema validation (`packages/rentl-schemas/src/rentl_schemas/config.py:275`).
- `testing/validate-generated-artifacts`: PASS — init tests validate generated config/seed against consuming schemas (`tests/unit/core/test_init.py:100`, `tests/integration/cli/test_init.py:198`).
- `testing/bdd-for-integration-quality`: PASS — onboarding/integration scenarios are BDD-based (`tests/integration/cli/test_onboarding_e2e.py:37`, `tests/integration/cli/test_init.py:38`).
- `testing/mandatory-coverage`: PASS — key onboarding behaviors have unit/integration/quality coverage (`tests/unit/core/test_doctor.py:789`, `tests/unit/core/test_init.py:396`, `tests/quality/cli/test_preset_validation.py:30`).
- `testing/make-all-gate`: PASS — `make all` executed in this audit and passed (`836 unit`, `91 integration`, `6 quality`).
- `global/no-placeholder-artifacts`: PASS — no placeholder values in generated onboarding artifacts (`packages/rentl-core/src/rentl_core/init.py:171`, `LICENSE:1`).

## Regression Check
- Prior audit-log entries show repeated churn around doctor/init summary/test coverage, but those fixes remain in place.
- New full-spec regression identified: doctor path-resolution drift vs config-path standard (not previously tracked in signposts or open fix items).

## Action Items

### Fix Now
- Resolve doctor path checks to use config-relative resolution before `check_workspace_dirs`/dependent checks, eliminating CWD-dependent false passes (`packages/rentl-core/src/rentl_core/doctor.py:262`, `packages/rentl-core/src/rentl_core/doctor.py:450`) (audit round 1).

### Deferred
- None.
