# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): FAIL — `MigrationStep` is missing the required transform-function reference field from the Task 2 contract.
- **Task 2** (round 2): PASS — Task 2 contract satisfied; `MigrationStep` transform-function reference field and related validation/serialization tests are present and passing.
- **Task 3** (round 1): FAIL — Transform lookup is keyed only by function name (collision bug), and migration type signatures violate `strict-typing-enforcement` via `Any`/untyped `dict`.
- **Task 3** (round 2): FAIL — Transform collision fix is verified, but migration typing still violates `strict-typing-enforcement` by using `object` in `ConfigDict`.
- **Task 3** (round 3): PASS — `ConfigDict` now uses a recursively-typed `ConfigValue` alias (no `Any`/`object`), and Task 3 migration registry/engine tests pass.
- **Task 4** (round 1): FAIL — `rentl migrate` completes but leaves `project.schema_version` unchanged (`0.0.1`), because the seed transform writes a top-level `schema_version` field instead.
- **Task 4** (round 2): PASS — Seed migration now updates `project.schema_version` correctly, and Task 4 migrate/dry-run/backup coverage passes.
- **Task 5** (round 1): PASS — Auto-migration runs before validation with backup-first writes, source/target migration output, and passing unit/integration/check gates.
- **Demo** (run 1): FAIL — Steps 1-3, 5 pass (migrate command, dry-run, backup, already-current). Step 4 fails: `rentl doctor` does not auto-migrate outdated configs. Root cause: doctor.py bypasses CLI's auto-migration path. Task 7 added to plan.md.
- **Task 7** (round 1): FAIL — Doctor auto-migration logic is implemented, but the required integration test file `tests/integration/core/test_doctor.py` is missing; coverage was added only at unit level.
- **Task 7** (round 2): PASS — Integration test coverage added for doctor auto-migration with full backup and validation flow.
- **Demo** (run 2): PASS — All steps passed: migrate command, dry-run, backup, auto-migration on doctor load, and already-current detection work correctly.
