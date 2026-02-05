---
description: Address action items from an audit that were marked "Fix Now".
---

# Fix Spec

Reads `audit.md`, fixes each “Fix Now” item, and runs `make all`.

## Important Guidelines

- **Autonomous execution** — user already approved these items in audit
- **Keep fixes minimal and targeted**
- **Run `make all` once at the end**

## Prerequisites

1. `agent-os/specs/{folder-name}/audit.md` exists
2. “Fix Now” items are present

If missing, stop and explain what’s needed.

## Process

### Step 1: Resolve the Spec

Preferred inputs: issue number/URL or `spec_id`.

Resolution order:
1. Use issue from user input (via `gh issue view`).
2. If missing, read `plan.md` for `spec_id` and `issue:` metadata.
3. If still ambiguous, list spec folders and ask the user.

### Step 2: Read `audit.md` and Extract Fix Now Items

If none, exit with:

```
No action items marked “Fix Now”. Run /audit-spec to verify completion.
```

### Step 3: Apply Fixes

For each item:
1. Open file at cited line
2. Apply minimal fix
3. Note what changed

Ask only if an item is ambiguous.

### Step 4: Verify

Run:

```
make all
```

Fix failures and re-run until green.

### Step 5: Report

- Summarize fixes
- Note verification result
- Update the existing “Spec Progress” comment on the spec issue (create it once if missing)

## Success Criteria

All Fix Now items addressed and `make all` passes.

## Workflow

```
shape-spec → do-spec → audit-spec → fix-spec → (repeat) → walk-spec → PR
```

Next step after this command: run `/audit-spec`.
