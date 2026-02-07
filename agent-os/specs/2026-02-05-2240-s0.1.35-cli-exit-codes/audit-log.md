# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 3** (round 1): FAIL — `ErrorResponse` construction in JSON export ValueError path omits required `exit_code`, causing runtime validation failure on that branch.
- **Task 3** (round 2): PASS — Export `ValueError` path now routes through `_error_from_exception` and test coverage verifies `error.exit_code` is present.
- **Task 4** (round 1): FAIL — `status --json` FAILED/CANCELLED path raises `typer.Exit` inside a broad `except Exception`, triggering `_error_from_exception` on `Exit("")` and crashing with `ValidationError` instead of returning orchestration exit code `20`.
- **Task 4** (round 2): PASS — `status` now re-raises intentional `typer.Exit` and regression tests confirm FAILED/CANCELLED JSON status returns stable orchestration exit code `20` with a valid data envelope.
- **Demo** (run 1): PASS — All 5 demo steps passed: success case (exit 0), config error (exit 10), validation error (exit 11), JSON mode with exit codes, and shell script branching on exit codes.
- **Spec Audit** (round 1): PASS — Performance 5/5, Intent 5/5, Completion 5/5, Security 5/5, Stability 5/5; fix-now count 0.
