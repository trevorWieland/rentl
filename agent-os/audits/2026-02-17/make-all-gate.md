---
standard: make-all-gate
category: testing
score: 78
importance: High
violations_count: 2
date: 2026-02-17
status: violations-found
---

# Standards Audit: Make All Gate

**Standard:** `testing/make-all-gate`
**Date:** 2026-02-17
**Score:** 78/100
**Importance:** High

## Summary

The repository defines a working `make all` gate and the spec workflow is designed to call it before final spec completion. However, merge-time enforcement is not guaranteed: the gate command is configurable and can be replaced, and there is no tracked CI workflow file in-repo that requires `make all` before merging. The local process is mostly compliant, but the gate is not consistently hard-enforced at the merge boundary.

## Violations

### Violation 1: `make all` is configurable and can be replaced in the spec gate path

- **File:** `agent-os/scripts/orchestrate.sh:196-197,680`
- **Severity:** Medium
- **Evidence:**
  ```bash
  TASK_GATE="${ORCH_TASK_GATE:-make check}"
  SPEC_GATE="${ORCH_SPEC_GATE:-make all}"
  ...
  if ! run_gate "make all" "$SPEC_GATE"; then
  ```
- **Recommendation:** Hard-lock the spec merge gate to `make all` in the release path, or add validation in `run_gate`/orchestrator startup that rejects non-`make all` values unless explicitly running a nonstandard mode.

### Violation 2: No in-repo CI merge gate is present for `make all`

- **File:** `Makefile:95-103`
- **Severity:** High
- **Evidence:**
  ```text
  make-all-gate standard states: "`make all` must pass before merge" (`agent-os/standards/testing/make-all-gate.md:3`)

  $ ls -la
  drwxr-xr-x 3 trevor trevor    4096 Feb 17 21:16 .claude
  ...
  drwxr-xr-x 8 trevor trevor    4096 Feb 17 21:10 agent-os
  drwxr-xr-x 5 trevor trevor    4096 Jan 25 10:55 tests
  
  $ rg --files -g '.github/workflows/*' -g '.gitlab-ci.yml' -g 'azure-pipelines.yml' -g 'Jenkinsfile'
  # (no output)
  ```
- **Recommendation:** Add a repository CI workflow (e.g., `.github/workflows/ci.yml`) that runs `make all` and block merge unless that check passes.

## Compliant Examples

- `Makefile:95-103` — `all` includes `format`, `lint`, `type`, `unit`, `integration`, and `quality` in sequence.
- `CONTRIBUTING.md:33-39` — documents the two-tier workflow with spec finalization on `make all`.
- `.claude/commands/agent-os/walk-spec.md:47-55` — requires `make all` before completing the final validation walkthrough.

## Scoring Rationale

- **Coverage:** Most workflow docs and orchestrator stages reference `make all`, but no merge gate in CI means enforcement is incomplete.
- **Severity:** One high-severity process gap (no merge-level gate) and one medium-severity bypass vector reduce reliability.
- **Trend:** Documentation and local commands consistently target `make all`, but enforcement constraints have not been hardened for merge operations.
- **Risk:** Medium-to-high risk of merge without full verification in non-standard execution paths.
