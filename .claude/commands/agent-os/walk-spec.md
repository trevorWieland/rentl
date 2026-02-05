# Walk Spec

Manual validation and sign-off. Ends by submitting a PR.

## Important Guidelines

- Human-in-the-loop — this is a manual review checkpoint
- Do not skip validation
- Submit PR at the end

## Prerequisites

1. Spec implementation complete
2. Latest audit pass or conditional pass
3. Working tree clean or changes committed

## Process

### Step 1: Resolve the Spec

Preferred inputs: issue number/URL or `spec_id`.

Resolution order:
1. Use issue from user input (via `gh issue view`).
2. If missing, read `plan.md` for `spec_id` and `issue:` metadata.
3. If still ambiguous, list spec folders and ask the user.

### Step 2: Manual Validation Checklist

Use AskUserQuestion to confirm:

```
Manual validation checklist (confirm each):
1. Behavior matches plan.md scope
2. Acceptance criteria met
3. make all passed
4. No unresolved audit items
```

### Step 3: Prepare PR

1. Ensure branch is up to date.
2. Create a PR using `gh pr create` with:
   - Title: `{spec_id} {short title}`
   - Summary of changes
   - Link to spec issue

### Step 4: Report

- Share PR URL
- Note any follow-ups

## Success Criteria

Manual validation complete and PR submitted.

## Workflow

```
shape-spec → do-spec → audit-spec → fix-spec → (repeat) → walk-spec → PR
```

Next step after this command: monitor PR checks and merge when ready.
