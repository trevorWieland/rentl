# Do Spec

Implement a shaped spec from the saved plan and run verification.

## Important Guidelines

- Autonomous execution — no shaping or interviewing
- Use the saved plan — Task 1 is already completed
- Run `make all` once at the end

## Prerequisites

1. A spec folder exists in `agent-os/specs/` with `plan.md`
2. Task 1 (Save Spec Documentation) is complete

If missing, stop and explain what’s needed.

## Process

### Step 1: Resolve the Spec

Preferred inputs: issue number/URL or `spec_id`.

Resolution order:
1. Use issue from user input (via `gh issue view`).
2. If missing, read `plan.md` for `spec_id` and `issue:` metadata.
3. If still ambiguous, list spec folders and ask the user.

### Step 2: Execute Plan Tasks

1. Read `plan.md` and identify Tasks 2..N.
2. Implement each task in order.
3. Keep changes scoped to the plan and standards.

### Step 3: Verification

Run:

```
make all
```

Fix failures and re-run until green.

### Step 4: Report

- Summarize changes
- Note verification result
- Update the existing “Spec Progress” comment on the issue (create it once if missing)

## Success Criteria

All plan tasks completed and `make all` passes.

## Workflow

```
shape-spec → do-spec → audit-spec → fix-spec → (repeat) → walk-spec → PR
```

Next step after this command: run `/audit-spec`.
