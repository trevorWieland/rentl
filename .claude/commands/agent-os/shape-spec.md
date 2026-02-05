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

### Step 1.5: Plan Mode Boundary

Plan mode is discussion only. Do **not** create branches or write files while in plan mode.
Branch creation, spec docs, and commits happen after the user switches to build mode.

If no issue was provided, use AskUserQuestion:

```
Do you want me to create a new spec issue on GitHub before shaping?

1. I have an existing issue
2. Create a new issue now
3. Pick the next best issue from the roadmap
```

If picking the next best issue:

1. Query GitHub for unblocked issues with `type:spec` and `status:planned`:

```
gh issue list --label "type:spec" --label "status:planned" --json number,title,labels,milestone,body,updatedAt --limit 50
```
2. Prefer the earliest version milestone (v0.1 → v1.0).
3. Present the top 3 candidates and pick the user’s choice.

If using an existing issue:

1. Ask for the issue number or URL.

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

Plan quality requirements:

- Each task must include concrete steps and referenced files (paths or modules).
- Include test expectations per task where relevant.
- Add acceptance checks tied to user value.

### Step 9: Save Spec Metadata

Include these fields at the top of `plan.md` and `shape.md`:

```
spec_id: sX.Y.ZZ
issue: https://github.com/OWNER/REPO/issues/NNN
version: vX.Y
```

### Step 10: Switch to Build Mode

Prompt the user to switch out of plan mode. Only proceed once confirmed.

### Step 11: Create Branch, Save Spec Docs, Commit, and Publish (Build Mode)

1. Create the issue branch via `gh issue develop` and check it out.
2. Create the spec folder and write `plan.md`, `shape.md`, `standards.md`, `references.md`, and any visuals.
3. Commit **only** the spec docs on the issue branch.
4. Update the **issue body** (do not post a new comment) with a “Spec Summary” section that includes:
   - Spec folder path
   - Plan summary (tasks and acceptance checks)
   - References and standards applied
5. Push the branch with `-u` to publish it.

### Step 12: Stop and Handoff

Do not start implementation.
Next step is `/do-spec`.

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
