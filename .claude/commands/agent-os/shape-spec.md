# Shape Spec

Gather context and structure planning for significant work. **Run this command while in plan mode.**

## Important Guidelines

- Always use AskUserQuestion tool when asking the user anything
- Offer suggestions — present options the user can confirm or adjust
- Keep it lightweight — this is shaping, not exhaustive documentation
- Prefer GitHub issues as the source of truth for spec id, title, status, and dependencies

## Prerequisites

This command must be run in plan mode.

If not in plan mode, stop immediately and say:

```
Shape-spec must be run in plan mode. Please enter plan mode first, then run /shape-spec again.
```

## Process

### Step 1: Resolve the Spec Issue (Preferred)

If the user provided an issue number, URL, or spec id:

1. Fetch the issue via `gh issue view` to get title, body, labels, milestone, and relationships.
2. Extract `spec_id`, `version` (from `version:*` label), and dependencies (blocked-by relationships).

If no issue was provided, use AskUserQuestion:

```
Do you want me to create a new spec issue on GitHub before shaping?

1. Yes — create an issue now
2. No — I will provide an existing issue
```

If creating a new issue:

1. Determine the next available `spec_id` by scanning GitHub issues for the target version.
2. Create the issue with labels `type:spec`, `status:planned`, `version:vX.Y` and set the milestone.
3. Use the new issue as the shaping context.

### Step 2: Clarify What We’re Building

Use the issue title/body as the primary scope. Ask only if unclear:

```
I pulled scope from the issue. Any constraints or expected outcomes I should add?
```

### Step 3: Gather Visuals (Optional)

```
Any visuals to reference? (mockups, screenshots, examples, or “none”)
```

### Step 4: Reference Implementations (Optional)

```
Is there similar code in this codebase I should reference? (paths or “none”)
```

### Step 5: Product Context (Quick Alignment)

If `agent-os/product/` exists, skim key files and ask:

```
Any product goals or constraints this spec should align with?
```

### Step 6: Standards

Read `agent-os/standards/index.yml` and propose relevant standards. Confirm with AskUserQuestion.

### Step 7: Spec Folder Name (Include Spec ID)

Create:

```
YYYY-MM-DD-HHMM-{spec_id}-{feature-slug}/
```

### Step 8: Plan Structure

Task 1 must always be Save Spec Documentation. Final task must run `make all`.

### Step 9: Save Spec Metadata

Include these fields at the top of `plan.md` and `shape.md`:

```
spec_id: sX.Y.ZZ
issue: https://github.com/OWNER/REPO/issues/NNN
version: vX.Y
```

### Step 10: Save Spec Docs and Commit

1. Create the spec folder and write `plan.md`, `shape.md`, `standards.md`, `references.md`, and any visuals.
2. Commit **only** the spec docs on the issue branch.
3. Post the spec folder path and plan link to the GitHub issue.

## Output Structure

```
agent-os/specs/{YYYY-MM-DD-HHMM-spec_id-feature-slug}/
├── plan.md
├── shape.md
├── standards.md
├── references.md
└── visuals/
```

## Workflow

```
shape-spec → do-spec → audit-spec → fix-spec → (repeat) → walk-spec → PR
```

Next step after this command: run `/do-spec`.
