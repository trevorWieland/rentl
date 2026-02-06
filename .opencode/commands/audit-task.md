# Audit Task

Audit the most recently completed task. Lightweight, focused, fast. Fully autonomous — no user interaction.

**Suggested model:** Different model from do-task for independence (e.g., Codex medium reasoning via headless CLI).

## Important Guidelines

- Audit only the most recent task — not the full spec
- Be specific in citations — file:line references and standard rule names
- If issues found, uncheck the task and add concrete fix items — don't just describe what's wrong
- Never modify spec.md
- Signposts must include evidence (exact errors, code snippets, or command output)

## Prerequisites

1. A spec folder exists with `spec.md`, `plan.md`, and `standards.md`
2. At least one task has been checked off in plan.md
3. The most recent task has a corresponding commit

If missing, exit with `audit-task-status: error` and explain what's needed.

## Process

### Step 1: Resolve the Spec

Preferred inputs: spec folder path, issue number/URL, or `spec_id`.

Resolution order:
1. Use spec folder from input if provided.
2. Read `plan.md` for `spec_id` and `issue:` metadata.
3. If ambiguous, exit with `audit-task-status: error`.

### Step 2: Identify the Task

Read plan.md and find the most recently checked-off top-level `[x]` task (not indented fix items — those are sub-items). This is the task to audit.

### Step 3: Load Context

Read these files:

- **spec.md** — acceptance criteria and non-negotiables (the contract)
- **plan.md** — the task description and its sub-items
- **standards.md** — applicable standards
- **The implementation** — use `git diff HEAD~1` (or the task's commit) to see exactly what changed. Also read the full files at cited locations for broader context.

### Step 4: Evaluate

Check the implementation against these criteria:

1. **Task fidelity** — Does the implementation match what the task description asked for? Are all sub-items addressed?
2. **Non-negotiable compliance** — Any violations of the non-negotiables from spec.md? These are hard failures — no exceptions.
3. **Standards adherence** — Any standards violations in the changed files? Cite specific rules and file:line locations.
4. **Quality** — Any obvious issues?
   - Dead code or commented-out code
   - Missing error handling at system boundaries
   - Untested code paths that should be tested
   - Naming inconsistencies
   - Security concerns (injection, hardcoded credentials, etc.)

Do NOT check:
- Overall spec completeness (that's audit-spec's job)
- Whether the demo passes (that's run-demo's job)
- Code that wasn't changed by this task

### Step 5: Verdict

**If the task passes:**
- Confirm it's clean
- Skip to Step 7

**If issues are found:**
1. Uncheck the task: `[x]` → `[ ]` in plan.md
2. Append specific fix items as indented `[ ]` entries below the task:
   ```
   - [ ] Task 6: Use OpenRouterModel for OpenRouter endpoints
     - [ ] Fix: Missing type annotation on routing_settings field (audit round N)
     - [ ] Fix: Dead import of PromptedOutput in runtime.py:3 (audit round N)
   ```
3. Each fix item must be specific enough that do-task can address it without ambiguity. Include file:line references.

### Step 6: Signpost (If Needed)

If the audit revealed a non-obvious issue or a pattern that future tasks should know about, write a signpost to signposts.md with:

- **Task:** which task number
- **Problem:** what was found
- **Evidence:** exact code snippet, error, or standard violation with file:line
- **Impact:** why this matters for future tasks

### Step 7: Update Audit Log

Append a brief entry to audit-log.md:

```
- **Task N** (round R): PASS|FAIL — [one-line summary]
```

If audit-log.md doesn't exist, create it with the standard header:

```markdown
# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task N** (round R): PASS|FAIL — [one-line summary]
```

### Step 8: Commit

Commit changes to plan.md, audit-log.md, and signposts.md (if modified):

```
git add plan.md audit-log.md signposts.md
git commit -m "Audit: Task N — PASS|FAIL"
```

### Step 9: Exit

Print one of these exit signals (machine-readable):

- `audit-task-status: pass` — task is clean, no issues
- `audit-task-status: fail` — task unchecked, fix items added to plan.md
- `audit-task-status: error` — prerequisites missing or unrecoverable issue

## Does NOT

- Score rubrics (that's audit-spec)
- Check overall spec completeness (that's audit-spec)
- Run the demo or verification gates (orchestrator handles gates)
- Fix code (it adds fix items for do-task)
- Push, create PRs, or touch GitHub
- Modify spec.md

## Workflow

```
shape-spec → [orchestrator: do-task ↔ audit-task loop → run-demo → audit-spec] → walk-spec → PR
```

Next step after this command: the orchestrator checks for remaining unchecked tasks. If more tasks exist, invoke do-task. If all tasks are done, proceed to the spec gate (`make all`) and then run-demo.
