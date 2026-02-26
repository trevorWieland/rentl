# Triage Gate

Investigate gate failures, identify root causes, and add structured fix items to plan.md. Fully autonomous — no user interaction. Does NOT fix code itself.

**Suggested model:** Different model from do-task for independence (e.g., Codex medium reasoning via headless CLI).

## Important Guidelines

- Investigate root causes — don't just parrot the error messages back as fix items
- One root cause = one fix item, even if it produces multiple symptoms
- Be specific in citations — file:line references
- Never modify spec.md
- Signposts must include evidence (exact errors, code snippets, or command output)

## Anti-Patterns (Explicit Prohibitions)

These are NEVER acceptable fix items, regardless of the gate failure:

- **Never increase timeouts** — violates `test-timing-rules`. If a test is slow, the fix is the code under test, not the timeout.
- **Never skip or delete tests** — violates `no-test-skipping`. If a test fails, the code is wrong, not the test.
- **Never add `# type: ignore`** — violates `strict-typing-enforcement`. Fix the type error properly.
- **Never chase symptoms** — if 5 tests fail because of one bad import, that's one fix item (fix the import), not 5.

## Prerequisites

1. A spec folder exists with `spec.md`, `plan.md`, and `standards.md`
2. Gate output is provided (the failing output from `make check` or `make all`)

If missing, exit with `triage-gate-status: error` and explain what's needed.

## Process

### Step 1: Resolve the Spec

Preferred inputs: spec folder path, issue number/URL, or `spec_id`.

Resolution order:
1. Use spec folder from input if provided.
2. Read `plan.md` for `spec_id` and `issue:` metadata.
3. If ambiguous, exit with `triage-gate-status: error`.

### Step 2: Load Context

Read these files:

- **spec.md** — acceptance criteria and non-negotiables (the contract)
- **plan.md** — tasks, completion status, and existing fix items
- **standards.md** — applicable standards (especially `test-timing-rules`, `no-test-skipping`, `strict-typing-enforcement`)
- **signposts.md** (if it exists) — known issues, resolutions, and architectural constraints. Pay attention to the **Status** field on each entry.
- **audit-log.md** (if it exists) — history of previous audits and triage rounds

### Step 3: Parse Gate Output

Classify each failure in the gate output:

- **format** — formatting issues (ruff format, black, prettier, etc.)
- **lint** — linter violations (ruff check, eslint, etc.)
- **type** — type checker errors (ty, mypy, pyright, tsc, etc.)
- **test** — test failures (pytest, jest, etc.)
- **coverage** — coverage threshold violations

Group failures by category. Note the file:line for each.

### Step 4: Investigate Root Causes

For each failure (or group of related failures):

1. **Read the source** at the cited file:line. Don't stop at the error message — understand the surrounding code.
2. **Trace the root cause** — ask *why* this fails, not just *what* fails. A type error might be caused by a wrong return type three functions up. Five test failures might share one broken fixture.
3. **Group symptoms by shared root cause** — if multiple failures trace back to the same underlying issue, they get ONE fix item, not N.
4. **Check whether the fix is obvious** — if it's a one-line typo or missing import, say so in the fix item. If it requires investigation, say that too.

### Step 5: Cross-Reference Signposts

**Before writing any fix items**, check signposts.md for related entries:

1. For each root cause you found in Step 4, search signposts.md for entries about the same problem (match by task number, file references, and problem description).
2. If a signpost with **Status: resolved** exists for the issue:
   - **Verify the resolution is actually implemented in code.** Read the files cited in the signpost's Solution/Resolution fields.
   - If the resolution is implemented and working: **do NOT add a fix item**. Note in the audit log that the resolution was verified but the gate still fails (new issue).
   - If the resolution is implemented but broken: add a fix item that references the signpost and explains what's still wrong (with new evidence).
   - If the resolution was NOT implemented: add a fix item, but reference the signpost's proposed solution as the recommended approach.
3. If a signpost documents an **architectural constraint** (e.g., "X is infeasible because Y"), verify the constraint by reading the cited code. Do NOT add fix items that ask do-task to do something the signpost proves is architecturally impossible.
4. If a signpost with **Status: deferred** exists: skip it — it's been explicitly deferred to a future spec.

### Step 6: Identify Affected Task(s)

Determine which task(s) own the failing code:

- **For task gate failures** (`make check`): the affected task is the most recently completed task (the one that just ran).
- **For spec gate failures** (`make all`): trace each failure to its owning task by matching file paths in the gate output to files modified by each task. Use `git log --oneline -- <file>` if needed to find which task commit introduced the change.

### Step 7: Add Fix Items

For each affected task:

1. **Uncheck the task:** `[x]` → `[ ]` in plan.md
2. **Add indented fix items** below the task:
   ```
   - [ ] Task N: <description>
     - [ ] Fix: [Gate] <root cause description> (<file>:<line>) (gate triage round R)
   ```
3. Each fix item must describe the **root cause and what needs to change**, not just the symptom. Include file:line references.
4. If a related signpost exists, reference it: `(see signposts.md: Task N, <problem summary>)`
5. Determine the triage round number R from existing fix items — count `(gate triage round N)` entries under this task and increment.

### Step 8: Signpost (If Needed)

If the investigation revealed a non-obvious root cause or a pattern that future tasks/triage should know about, write a signpost to signposts.md with:

- **Task:** which task number
- **Status:** `unresolved`
- **Problem:** what was found (the root cause, not the symptom)
- **Evidence:** exact error output, code snippet, or standard violation with file:line
- **Impact:** why this matters and what to watch for

Do NOT write a signpost for straightforward issues (missing import, typo, etc.).

### Step 9: Update Audit Log

Append a brief entry to audit-log.md:

```
- **Gate triage** (round R): <category> failures — <one-line root cause summary>
```

If audit-log.md doesn't exist, create it with the standard header:

```markdown
# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Gate triage** (round R): <category> failures — <one-line root cause summary>
```

### Step 10: Commit

Commit changes to plan.md, audit-log.md, and signposts.md (if modified):

```
git add plan.md audit-log.md signposts.md
git commit -m "Gate triage round R: <brief summary>"
```

Only include files that were actually modified.

### Step 11: Exit

Print one of these exit signals (machine-readable):

- `triage-gate-status: diagnosed` — root cause(s) identified, fix items added to plan.md
- `triage-gate-status: blocked` — cannot diagnose or the issue requires human intervention (e.g., environmental, infrastructure, or architectural deadlock)
- `triage-gate-status: error` — prerequisites missing or unrecoverable issue

## Does NOT

- Fix code (it adds fix items for do-task)
- Run tests or verification gates (orchestrator handles gates)
- Score rubrics (that's audit-spec)
- Check overall spec completeness (that's audit-spec)
- Push, create PRs, or touch GitHub
- Modify spec.md
- Increase timeouts, skip tests, or add type: ignore

## Workflow

```
do-task → make check FAILS → triage-gate (investigates, adds fix items) → do-task (picks up fix items) → make check
```

This command bridges the gap between a raw gate failure and an informed do-task retry. Instead of throwing error output at do-task blindly, triage-gate investigates the root cause and adds structured fix items with full context.
