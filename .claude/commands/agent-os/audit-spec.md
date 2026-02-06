# Audit Spec

Bird's-eye audit of the full implementation after all tasks and demo pass. Score rubrics, check non-negotiables, verify standards adherence, detect regressions. Fully autonomous — no user interaction.

**Suggested model:** Strong reasoner, different from do-task (e.g., Codex high reasoning via headless CLI). Deep review — quality matters more than speed.

## Important Guidelines

- This is the full-picture audit — check everything, not just the latest task
- Non-negotiables are hard pass/fail — no exceptions, no caveats
- Be specific in citations — file:line and standard rule references
- Write machine-readable status in audit.md so the orchestrator can parse it
- Never modify spec.md
- Prefer GitHub issues for deferrals instead of editing roadmap.md

## Prerequisites

1. A spec folder exists with `spec.md`, `plan.md`, `standards.md`, and `demo.md`
2. All tasks in plan.md are checked off
3. Demo has been run (results in demo.md)
4. If the full verification gate wasn't run, note it in the audit instead of stopping

## Process

### Step 1: Resolve the Spec

Preferred inputs: spec folder path, issue number/URL, or `spec_id`.

Resolution order:
1. Use spec folder from input if provided.
2. Read `plan.md` for `spec_id` and `issue:` metadata.
3. If ambiguous, exit with error.

### Step 2: Load Context

Read all spec files — do not ask the user for summaries:

- **spec.md** — acceptance criteria, non-negotiables (the contract)
- **plan.md** — tasks, fix items, completion status
- **standards.md** — applicable standards
- **references.md** — related files and resources
- **demo.md** — demo plan and results
- **signposts.md** — known issues and workarounds
- **audit-log.md** — history of task audits and demo runs (check for regressions)
- **Implementation files and tests** referenced by the plan

### Step 3: Perform Audit

Evaluate the full implementation across these dimensions:

#### 3a: Rubric Scores (1-5)

Score each dimension:

- **Performance** — Is the implementation efficient? No unnecessary computation, I/O, or memory usage?
- **Intent** — Does the implementation match the spec's stated goals? Does it solve the right problem?
- **Completion** — Are all acceptance criteria met? Any gaps or partial implementations?
- **Security** — No injection vulnerabilities, hardcoded credentials, unsafe deserialization, or other OWASP concerns?
- **Stability** — Proper error handling, no silent failures, resilient to edge cases?

#### 3b: Non-Negotiable Compliance

Check every non-negotiable from spec.md's **Note to Code Auditors** section. For each one:

- Explicitly state **PASS** or **FAIL**
- Cite evidence (file:line reference, code snippet, or command output)

Non-negotiable failures are automatic audit failures regardless of rubric scores.

#### 3c: Standards Adherence

Check all applicable standards from standards.md across the full implementation (not just per-task diffs). For each violation:

- Cite the standard rule
- Cite the file:line where the violation occurs
- Classify severity: High / Medium / Low

#### 3d: Demo Status

Check demo.md Results:

- Did the demo pass?
- Are the results convincing?
- Were any steps skipped? If so, is the justification reasonable?

If the demo was not run, flag it as a **Fix Now** action item.

#### 3e: Regression Check

Review audit-log.md for patterns:

- Tasks that failed and were fixed — have they regressed?
- Recurring issues across multiple tasks
- Signposts that suggest systemic problems

#### 3f: Cross-Cutting Concerns

Things that only emerge at the full-picture level:

- Consistency across files (naming, patterns, conventions)
- Architectural coherence
- Test coverage gaps that span multiple tasks

### Step 4: Categorize Action Items

Use the default routing:

```
High/Medium severity → Fix Now
Low severity → Defer
```

**Fix Now items:**
- Append as new `[ ]` entries at the bottom of plan.md's Tasks section
- Each item must include file:line citations and clear fix description

**Deferred items:**
1. Determine the next available `spec_id` from GitHub issues for the target version.
2. Create a GitHub issue with:
   - Title: `{spec_id} {short title}`
   - Labels: `type:spec`, `status:planned`, `version:vX.Y`
   - Milestone: target version
   - Body: context and link to the current spec issue
3. Record the new issue URL in audit.md.

Do **not** edit roadmap.md during audit.

### Step 5: Write audit.md

Write audit.md with a machine-readable header followed by the full audit report:

```markdown
status: pass|fail
fix_now_count: N

# Audit: {spec_id} {title}

- Spec: {spec_id}
- Issue: {issue_url}
- Date: YYYY-MM-DD
- Round: N

## Rubric Scores (1-5)
- Performance: N/5
- Intent: N/5
- Completion: N/5
- Security: N/5
- Stability: N/5

## Non-Negotiable Compliance
1. [Non-negotiable 1]: **PASS|FAIL** — [evidence with file:line]
2. [Non-negotiable 2]: **PASS|FAIL** — [evidence with file:line]

## Demo Status
- Latest run: PASS|FAIL (Run N, date)
- [Summary of results]

## Standards Adherence
- [Standard]: [PASS|violation with file:line citation]

## Regression Check
- [Findings from audit-log.md review]

## Action Items

### Fix Now
- [Item with file:line citation]

### Deferred
- [Item] → [GitHub issue URL]
```

**Status rules:**
- `status: pass` requires: all rubric scores 5/5, all non-negotiables PASS, demo PASS, zero Fix Now items
- `status: fail` if any of the above conditions aren't met

### Step 6: Update Audit Log

Append a brief entry to audit-log.md:

```
- **Spec Audit** (round N): PASS|FAIL — [rubric summary, fix-now count]
```

### Step 7: Report to GitHub

Update the existing "Spec Progress" comment on the spec issue (create it once if missing) with:

- Overall status and score
- Fix Now count
- Deferred issue links
- Demo status

### Step 8: Commit

Commit audit.md, audit-log.md, and plan.md changes:

```
git add audit.md audit-log.md plan.md
git commit -m "Spec audit round N: PASS|FAIL"
```

### Step 9: Exit

The exit signal is the `status:` field in audit.md (machine-readable):

- `status: pass` → orchestrator proceeds to notify human for walk-spec
- `status: fail` → orchestrator loops back to do-task to address Fix Now items

## Does NOT

- Fix anything (adds Fix Now items to plan.md for do-task)
- Run the demo itself (reads results from demo.md)
- Push or create PRs
- Touch roadmap.md
- Modify spec.md

## Success Criteria

All rubric scores are 5/5, all non-negotiables pass, demo passes, and no Fix Now items remain.

## Workflow

```
shape-spec → [orchestrator: do-task ↔ audit-task loop → run-demo → audit-spec] → walk-spec → PR
```

Next step after this command: if pass, the orchestrator notifies the human to run walk-spec. If fail, the orchestrator loops back to do-task.
