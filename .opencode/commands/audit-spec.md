---
description: Critique and score completed spec implementations across a 5-pronged rubric plus standards adherence.
---

# Audit Spec

Produces `audit.md` in the spec folder and logs decisions to GitHub issues.

## Important Guidelines

- **Always use question tool** when asking the user anything
- **Be specific in citations** — file:line, standard rule references
- **Prefer GitHub issues** for deferrals instead of editing `roadmap.md`

## Prerequisites

This command assumes:

1. A completed spec folder exists in `agent-os/specs/` with:
   - `plan.md`
   - `shape.md`
   - `standards.md`

2. Implementation is complete (or nearly complete). If `make all` wasn’t run, note it in the audit instead of stopping.

## Process

### Step 1: Resolve the Spec

Preferred inputs: issue number/URL or `spec_id`.

Resolution order:
1. Use issue from user input (via `gh issue view`).
2. If missing, read `plan.md` for `spec_id` and `issue:` metadata.
3. If still ambiguous, list spec folders and ask the user.

### Step 2: Gather Context

Read:
- `plan.md`, `shape.md`, `standards.md`
- `agent-os/product/mission.md`, `agent-os/product/roadmap.md`
- Implementation files and tests referenced by the plan

### Step 3: Perform Audit (Autonomous)

Score: Performance, Intent, Completion, Security, Stability (1–5). Check standards adherence and compile action items with file:line citations.

### Step 4: Categorize Action Items (Streamlined)

Ask once for default routing:

```
Default routing for action items?
1. High/Medium → Fix Now, Low → Defer (Recommended)
2. All → Fix Now
3. I will decide per item
```

Then only ask per-item when exceptions are needed.

#### Defer to Future Spec (GitHub)

When deferring:
1. Ask which milestone/version.
2. Determine the next available `spec_id` from GitHub issues for that version.
3. Create a GitHub issue with:
   - Title: `{spec_id} {short title}`
   - Labels: `type:spec`, `status:planned`, `version:vX.Y`
   - Milestone: target version
   - Body: include context and link to the current spec issue
4. Record the new issue URL in `audit.md`.

Do **not** edit `roadmap.md` during audit.

### Step 5: Generate `audit.md`

Include rubric scores, standards violations, and action items grouped by category. Note if `make all` wasn’t run.

### Step 6: Report to GitHub (Optional but Recommended)

Update the existing “Spec Progress” comment on the spec issue (create it once if missing) with:
- Overall score and status
- Fix Now count
- Deferred issue links

## Workflow

```
shape-spec → do-spec → audit-spec → fix-spec → (repeat) → walk-spec → PR
```

## Success Criteria

All rubric scores are 5/5 and no action items remain in “Fix Now”.

Next step after this command: run `/fix-spec` if any Fix Now items exist; otherwise run `/walk-spec`.
