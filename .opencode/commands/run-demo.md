# Run Demo

Execute the demo plan and validate it works. If it fails, investigate and route issues back to the task loop. Fully autonomous — no user interaction.

**Suggested model:** Capable implementer with good debugging skills (e.g., Sonnet via headless CLI).

## Important Guidelines

- Execute the demo — don't just read it and say it looks good
- If a step fails, investigate the root cause before adding tasks
- If tests pass but the demo fails, that's a test gap — identify what's missing
- Never fix code directly — add tasks to plan.md for do-task to pick up
- Never modify spec.md
- Signposts must include evidence

## Prerequisites

1. A spec folder exists with `spec.md`, `plan.md`, and `demo.md`
2. All tasks in plan.md are checked off
3. The full verification gate (`make all`) has passed

If missing, exit with `run-demo-status: error` and explain what's needed.

## Process

### Step 1: Resolve the Spec

Preferred inputs: spec folder path, issue number/URL, or `spec_id`.

Resolution order:
1. Use spec folder from input if provided.
2. Read `plan.md` for `spec_id` and `issue:` metadata.
3. If ambiguous, exit with `run-demo-status: error`.

### Step 2: Load Context

Read these files:

- **demo.md** — the demo steps and expected outcomes
- **spec.md** — acceptance criteria (for context on what the demo should prove)
- **signposts.md** (if it exists) — check for known issues that might affect the demo

### Step 3: Execute Demo

Run each demo step in order:

1. Read the step description and expected outcome
2. Execute the action (run the command, make the config change, call the API, etc.)
3. Observe the result
4. Compare against the expected outcome
5. Record the result

**If a step passes:** Note it and continue to the next step.

**If a step fails:** Stop executing further steps and proceed to Step 4 (Investigation).

**If a step cannot be executed** in the current environment (e.g., requires an external service that's not available, needs a GUI, etc.): Note what was verified instead and why the step couldn't be run. This is not a failure — but it must be clearly documented.

### Step 4: Investigate Failures

For each failed step:

1. **Read the error output** — what exactly went wrong?
2. **Check test coverage** — do existing tests cover the failing scenario?
   - If tests pass but the demo fails, this is a **test gap**. The test suite should guarantee the demo works. Identify what specific tests are missing.
3. **Trace the root cause** — read the relevant code, follow the execution path, identify where the behavior diverges from the expected outcome.
4. **Write a signpost** in signposts.md with:
   - The exact error or unexpected output
   - What the expected outcome was
   - The root cause (or best hypothesis if uncertain)
   - Which files/functions are involved
5. **Add tasks to plan.md** for do-task to fix:
   - If a test gap was found: add a task to write the missing test(s) first, then a task to fix the underlying issue
   - If the code is simply wrong: add a task describing the fix needed
   - Each new task must be specific enough for do-task to act on without ambiguity

### Step 5: Record Results

Append results to demo.md under `## Results`:

```markdown
### Run N — [context] (YYYY-MM-DD HH:MM)
- Step 1: PASS|FAIL — [brief note]
- Step 2: PASS|FAIL — [brief note]
- Step 3: SKIPPED — [reason]
- **Overall: PASS|FAIL**
```

If this is the first run, add the `## Results` header.

### Step 6: Update Audit Log

Append a brief entry to audit-log.md:

```
- **Demo** (run N): PASS|FAIL — [one-line summary]
```

If audit-log.md doesn't exist, create it with the standard header.

### Step 7: Commit

Commit demo.md, audit-log.md, signposts.md, and plan.md changes:

```
git add demo.md audit-log.md signposts.md plan.md
git commit -m "Demo run N: PASS|FAIL"
```

Only include files that were actually modified.

### Step 8: Exit

Print one of these exit signals (machine-readable):

- `run-demo-status: pass` — all steps passed
- `run-demo-status: fail` — one or more steps failed, tasks added to plan.md
- `run-demo-status: error` — prerequisites missing or unrecoverable issue

## Does NOT

- Fix code itself (it adds tasks for do-task to pick up)
- Modify spec.md
- Push or touch GitHub
- Score rubrics (that's audit-spec)
- Skip investigation — every failure must be diagnosed before adding tasks

## Workflow

```
shape-spec → [orchestrator: do-task ↔ audit-task loop → run-demo → audit-spec] → walk-spec → PR
```

Next step after this command: if pass, the orchestrator invokes audit-spec. If fail, the orchestrator loops back to do-task to address the newly added tasks.
