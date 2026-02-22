status: fail
fix_now_count: 4

# Audit: s0.1.43 Documentation Placeholders, CLI Surface & UX Polish

- Spec: s0.1.43
- Issue: https://github.com/trevorWieland/rentl/issues/130
- Date: 2026-02-22
- Round: 1

## Rubric Scores (1-5)
- Performance: 4/5
- Intent: 3/5
- Completion: 3/5
- Security: 5/5
- Stability: 2/5

## Non-Negotiable Compliance
1. No placeholder commands in user-facing docs: **PASS** — placeholder grep is clean for README/CONTRIBUTING/troubleshooting/workflow guides; only legitimate HTML tags remain in `agent-os/docs/WORKFLOW-GUIDE.md:264`, `agent-os/docs/WORKFLOW-GUIDE.md:265` and similar `<details>/<summary>` blocks.
2. Extracted core logic must not import CLI surface modules: **PASS** — `rg -n "^from rentl\\.|^import rentl\\." packages/rentl-core/src` returns no matches; extracted modules live in core (`packages/rentl-core/src/rentl_core/migrate.py:311`, `packages/rentl-core/src/rentl_core/secrets.py:33`).
3. No silent failures in user-facing operations: **FAIL** — watcher no-state path crashes before a diagnosable failure (`services/rentl-cli/src/rentl/main.py:3584` uses `dataclasses.replace` on a non-dataclass model), reproducing `Error: replace() should be called on dataclass instances` from `rentl status --watch`; and non-TTY `--json` output is polluted by auto-migration `print(...)` lines (`services/rentl-cli/src/rentl/main.py:2268`, `services/rentl-cli/src/rentl/main.py:2302`), breaking machine-readable diagnostics.
4. No test deletions or modifications to pass gates: **PASS** — no deleted test files in spec branch diff (`git diff --name-status origin/130-s0143-documentation-placeholders-cli-surface-ux-polish...HEAD -- tests` shows only `M`/`A`), with net additions in changed tests (`git diff --numstat ... -- tests`).

## Demo Status
- Latest run: PASS (Run 1, 2026-02-21)
- Demo.md records all 7 run steps passing, including `make all` and help/doc checks (`agent-os/specs/2026-02-21-1830-s0143-doc-placeholders-cli-ux-polish/demo.md:24`).
- Audit found post-demo regressions not covered by demo scenarios (`status --watch` no-state path and `--json` output during auto-migrate).

## Standards Adherence
- `ux/copy-pasteable-examples`: PASS — placeholder commands removed from targeted docs; examples resolve to concrete executable paths.
- `ux/stale-reference-prevention`: PASS — help/env verification paths are aligned with current CLI/docs (`packages/rentl-core/src/rentl_core/help.py:219`, `README.md:182`, `README.md:299`).
- `python/cli-help-docstring-gating`: PASS — required `\f` gates present (`services/rentl-cli/src/rentl/main.py:254`, `services/rentl-cli/src/rentl/main.py:271`, `services/rentl-cli/src/rentl/main.py:1292`, `services/rentl-cli/src/rentl/main.py:1451`).
- `architecture/thin-adapter-pattern`: **violation (High)** — CLI still owns migration planning/apply/backup/serialization workflow in `_auto_migrate_if_needed` (`services/rentl-cli/src/rentl/main.py:2200`, `services/rentl-cli/src/rentl/main.py:2251`, `services/rentl-cli/src/rentl/main.py:2287`) instead of delegating fully to core.
- `ux/trust-through-transparency`: **violation (High)** — watcher no-state path can terminate with a runtime exception instead of contextualized failure output (`services/rentl-cli/src/rentl/main.py:3333`, `services/rentl-cli/src/rentl/main.py:3584`).
- `ux/progress-is-product`: **violation (Medium)** — no-state watcher terminal path does not emit explicit failure reason before exit (`services/rentl-cli/src/rentl/main.py:3346`, `services/rentl-cli/src/rentl/main.py:3351`).
- `testing/mandatory-coverage`: **violation (Medium)** — no regression test covers auto-migration + `--json` output purity or no-state watcher failure path (gap evidenced by escaped regressions in `services/rentl-cli/src/rentl/main.py:2200` and `services/rentl-cli/src/rentl/main.py:3290`).
- `testing/make-all-gate`: PASS — latest documented gate run is green in demo (`agent-os/specs/2026-02-21-1830-s0143-doc-placeholders-cli-ux-polish/demo.md:31`).

## Regression Check
- Prior rounds repeatedly found edge-case gaps after initial fixes (Task 5 had two follow-up failures, Task 6 had follow-up export coverage fix) per `audit-log.md`.
- Current audit continues that pattern: Task 6 observability is green on covered paths but still regresses on untested no-state watch flow.

## Action Items

### Fix Now
- `services/rentl-cli/src/rentl/main.py:2200`: Move `_auto_migrate_if_needed` migration planning/apply/backup/serialization workflow into core (`rentl_core.migrate`) so CLI remains a thin adapter.
- `services/rentl-cli/src/rentl/main.py:2268`: Stop emitting plain-text auto-migration notices to stdout for `--json` commands; keep stdout JSON-only (stderr/logging/metadata are acceptable).
- `services/rentl-cli/src/rentl/main.py:3584`: Replace invalid `replace(...)` usage in no-state watch handling; current code crashes with `replace() should be called on dataclass instances`.
- `services/rentl-cli/src/rentl/main.py:3333`: Add explicit no-state failure context to watcher terminal output (reason + next action) so headless failures are diagnosable.

### Deferred
- None.
