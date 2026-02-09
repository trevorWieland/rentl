# Agent OS Workflow Guide

A spec-driven development workflow powered by AI agents and an automated orchestrator. Agent OS coordinates planning, implementation, auditing, and demo validation through a pipeline of specialized agent commands -- and it works with any tech stack.

## Table of Contents

- [System Overview](#system-overview)
- [Getting Started](#getting-started)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [The Full Lifecycle](#the-full-lifecycle)
- [Spec Folder Structure](#spec-folder-structure)
- [File Formats](#file-formats)
- [Core Commands](#core-commands)
  - [shape-spec](#shape-spec)
  - [do-task](#do-task)
  - [audit-task](#audit-task)
  - [run-demo](#run-demo)
  - [audit-spec](#audit-spec)
  - [walk-spec](#walk-spec)
- [The Orchestrator](#the-orchestrator)
- [Feedback and Blocker Commands](#feedback-and-blocker-commands)
  - [handle-feedback](#handle-feedback)
  - [resolve-blockers](#resolve-blockers)
- [Supporting Commands](#supporting-commands)
  - [plan-product](#plan-product)
  - [inject-standards](#inject-standards)
  - [discover-standards](#discover-standards)
  - [index-standards](#index-standards)
  - [sync-roadmap](#sync-roadmap)
- [Deprecated Commands](#deprecated-commands)
- [Verification Gates](#verification-gates)
- [The Signpost System](#the-signpost-system)
- [The Audit System](#the-audit-system)
- [GitHub Issues and Spec IDs](#github-issues-and-spec-ids)
- [Branching and PRs](#branching-and-prs)
- [Configuration Reference](#configuration-reference)
- [Adapting to Your Project](#adapting-to-your-project)
- [Design Principles](#design-principles)

---

## System Overview

Agent OS is a set of agent commands and an orchestrator script that automate a spec-driven development workflow. The workflow has two interactive bookends (human + agent collaboration) with a fully automated middle:

1. **shape-spec** (interactive) -- Human and agent collaborate to define what to build.
2. **orchestrate.sh** (automated) -- Agents implement, verify, audit, demo, and audit again in a loop.
3. **walk-spec** (interactive) -- Human validates the demo and submits the PR.

The key directories:

| Path | Purpose |
|------|---------|
| `.claude/commands/agent-os/` | Agent command definitions (markdown files) |
| `agent-os/scripts/` | Orchestrator script and supporting tools |
| `agent-os/standards/` | Project-specific coding standards (you create these) |
| `agent-os/product/` | Product documentation (mission, roadmap, tech stack) |
| `agent-os/specs/` | Spec folders (one per feature/task) |

---

## Getting Started

Agent OS is designed to be adopted into any existing project. Here is how to set it up from scratch:

### 1. Copy Agent OS into your project

Copy these directories into your repository:

- `.claude/commands/agent-os/` -- the agent command definitions
- `agent-os/scripts/` -- the orchestrator script

### 2. Set up verification gates

Agent OS expects two shell commands that run your project's test/lint/check suite:

- **Task gate** (default: `make check`) -- a fast check run after each task (e.g., format + lint + typecheck + unit tests).
- **Spec gate** (default: `make all`) -- a thorough check run after all tasks complete (e.g., everything in the task gate plus integration tests, quality checks, etc.).

You can use `make`, a shell script, `npm run`, `cargo`, or anything else. Configure them via `ORCH_TASK_GATE` and `ORCH_SPEC_GATE` environment variables. For example:

```bash
# Node.js project
ORCH_TASK_GATE="npm run lint && npm test" ORCH_SPEC_GATE="npm run test:all" ./agent-os/scripts/orchestrate.sh ...

# Rust project
ORCH_TASK_GATE="cargo clippy && cargo test" ORCH_SPEC_GATE="cargo test --all" ./agent-os/scripts/orchestrate.sh ...

# Go project
ORCH_TASK_GATE="go vet ./... && go test ./..." ORCH_SPEC_GATE="go test -race ./..." ./agent-os/scripts/orchestrate.sh ...

# Python project using make
ORCH_TASK_GATE="make check" ORCH_SPEC_GATE="make all" ./agent-os/scripts/orchestrate.sh ...
```

### 3. Initialize product documentation (optional but recommended)

Run `/plan-product` in Claude Code TUI to create foundational product docs:

```
agent-os/product/mission.md    -- what the product does and for whom
agent-os/product/roadmap.md    -- planned features and milestones
agent-os/product/tech-stack.md -- languages, frameworks, and tools
```

These files give shape-spec context about your product when planning new features.

### 4. Discover and document your coding standards (optional but recommended)

Run `/discover-standards` in Claude Code TUI to extract your project's tribal knowledge into documented standards:

```
agent-os/standards/index.yml          -- index of all standards
agent-os/standards/<topic>/<name>.md  -- individual standard files
```

Standards are injected into agent context during planning and implementation, helping agents follow your project's conventions.

### 5. Create your first spec

Run `/shape-spec` in Claude Code TUI to plan your first feature, then run the orchestrator to implement it. See [The Full Lifecycle](#the-full-lifecycle) for the complete walkthrough.

---

## Prerequisites

### Required by Agent OS

| Tool | Version | Purpose |
|------|---------|---------|
| [gh](https://cli.github.com/) | latest | GitHub CLI (issues, PRs, branches) |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | latest | Agent CLI for running commands (`claude -p` for headless) |
| make | any | Default verification gates (replaceable -- see [Adapting to Your Project](#adapting-to-your-project)) |
| bash | >= 4.0 | Orchestrator script |

### Project-specific (examples)

Your project will have its own runtime, package manager, and tools. For example:

| Tool | Example | Purpose |
|------|---------|---------|
| Language runtime | Python 3.x, Node 20, Go 1.22, Ruby 3.x | Your project's runtime |
| Package manager | uv, npm, cargo, bundler | Dependency management |
| Linter/formatter | ruff, eslint, clippy, rubocop | Code quality (used by verification gates) |
| Test runner | pytest, jest, cargo test, rspec | Tests (used by verification gates) |

See your project's README or CONTRIBUTING.md for project-specific setup instructions.

---

## Architecture

```
shape-spec (interactive)
    |
    v
 +--------------------------------------------------------------+
 |  orchestrate.sh (automated)                                   |
 |                                                               |
 |  for each unchecked task:                                     |
 |      do-task  -->  task gate  -->  audit-task                 |
 |                                                               |
 |  spec gate                                                    |
 |  run-demo  -->  if issues: adds tasks, loops back             |
 |                                                               |
 |  audit-spec  -->  if issues: adds tasks, loops back           |
 |               -->  if pass: notify human                      |
 +--------------------------------------------------------------+
    |
    v
walk-spec (interactive)  -->  PR
```

After the PR is created, two additional commands handle the review cycle:

```
walk-spec --> PR created --> reviewers comment --> handle-feedback --> [if tasks added: orchestrator --> walk-spec] --> merge

orchestrator halts --> user runs resolve-blockers --> resolve-blockers reconciles --> user re-runs orchestrator
```

---

## The Full Lifecycle

### Step 1: Shape the Spec (Interactive)

Run `/shape-spec` in Claude Code TUI (plan mode). The human and agent collaborate to:

1. Resolve the target GitHub issue (or create one).
2. Clarify scope, gather visuals, identify reference implementations.
3. Align with product context (from `agent-os/product/`, if set up).
4. Select applicable standards (from `agent-os/standards/index.yml`, if set up).
5. Define non-negotiables (verifiable, specific, important constraints for auditors).
6. Write acceptance criteria (the immutable contract).
7. Write a narrative demo plan.
8. Write the task plan (checklist in plan.md).
9. Create the branch (via `gh issue develop`), write spec files, commit, and push.

Output: A spec folder with `spec.md`, `plan.md`, `demo.md`, `standards.md`, `references.md`, and optionally `visuals/`. Task 1 ("Save Spec Documentation") is checked off.

### Step 2: Run the Orchestrator (Automated)

```bash
./agent-os/scripts/orchestrate.sh agent-os/specs/<your-spec-folder>
```

The orchestrator loops through:

1. **Task loop**: For each unchecked task in plan.md:
   - Invoke `do-task` to implement.
   - Run the task gate (configurable, default `make check`). If it fails, re-invoke `do-task` with the error output up to 3 times.
   - Invoke `audit-task` to audit. If it finds issues, it unchecks the task and adds fix items; the loop picks it up again.
2. **Spec gate**: Run the spec gate (configurable, default `make all`). If it fails, invoke `do-task` to fix.
3. **Demo**: Invoke `run-demo`. If it fails, new tasks are added and the loop restarts.
4. **Spec audit**: Invoke `audit-spec`. If it fails, new tasks are added and the loop restarts. If it passes, the orchestrator exits successfully.

The orchestrator stops when:
- The spec audit passes (`status: pass` in audit.md).
- Staleness is detected (plan.md unchanged for `ORCH_STALE_LIMIT` cycles).
- A task is stuck after `ORCH_MAX_TASK_RETRIES` attempts.
- The safety limit of `ORCH_MAX_CYCLES` is reached.
- An agent exits with `blocked` or `error`.

### Step 3: Walk and Submit (Interactive)

Run `/walk-spec` in Claude Code TUI. The agent:

1. Reads all spec artifacts and implementation files.
2. Runs the spec gate to confirm everything passes.
3. Presents an implementation summary with acceptance criteria evidence.
4. Walks the user through an interactive demo.
5. Creates the PR with spec summary, audit scores, and non-negotiable compliance.
6. Updates the roadmap.
7. Evaluates whether new standards should be discovered.
8. Pushes and reports the PR URL.

### Step 4: Handle Feedback (Interactive, If Needed)

After the PR is created and reviewers comment, run `/handle-feedback`. The agent:

1. Fetches all PR review comments, review bodies, issue-style comments, and check annotations.
2. Triages each piece of feedback (valid-actionable, valid-addressed, invalid, style-preference, out-of-scope, duplicate).
3. Presents the triage to the user for approval.
4. Executes approved actions: adds fix items to plan.md, posts reply comments, creates GitHub issues for out-of-scope items.
5. If fix items were added, the user re-runs the orchestrator.

### Step 5: Resolve Blockers (Interactive, If Needed)

If the orchestrator halts, run `/resolve-blockers`. The agent:

1. Investigates all spec artifacts, identifying unresolved signposts, contradictory fix items, stuck tasks, and architectural constraints.
2. Presents a blocker report with 2-3 resolution options per blocker.
3. The user picks an option; the agent reconciles artifacts.
4. The user re-runs the orchestrator.

---

## Spec Folder Structure

Each spec lives in `agent-os/specs/{YYYY-MM-DD-HHMM-spec_id-feature-slug}/`.

| File | Mutability | Purpose |
|------|------------|---------|
| `spec.md` | **Immutable** | Acceptance criteria, non-negotiables, Note to Code Auditors. The contract. |
| `plan.md` | Mutable | Checklist tasks (`[ ]`/`[x]`), fix items added by audits. The work tracker. |
| `demo.md` | Plan: immutable, Results: append-only | Narrative demo plan + recorded results per run. |
| `standards.md` | Static | Applicable standards for this spec. |
| `references.md` | Static | Implementation files, issues, related specs. |
| `signposts.md` | Append-only (Status field can be updated) | Problems encountered with mandatory evidence. |
| `audit-log.md` | Append-only | Running history of task audits, demo runs, spec audits. |
| `audit.md` | Overwritten per audit | Latest spec audit with machine-readable `status:` header. |
| `visuals/` | Static | Optional mockups, diagrams, screenshots. |

Key invariant: **spec.md is never modified by automated commands.** If an agent modifies spec.md, the orchestrator reverts it and amends the commit (self-heal). The only command that can modify spec.md is resolve-blockers, and only with explicit user approval after presenting the exact diff.

---

## File Formats

### spec.md

```markdown
spec_id: sX.Y.ZZ
issue: https://github.com/OWNER/REPO/issues/NNN
version: vX.Y

# Spec: [Title]

## Problem
[Brief statement of what's broken or missing]

## Goals
- [Goal 1]
- [Goal 2]

## Non-Goals
- [Explicit exclusion 1]
- [Explicit exclusion 2]

## Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **[Non-negotiable 1]** -- [explanation]
2. **[Non-negotiable 2]** -- [explanation]
```

### plan.md

```markdown
spec_id: sX.Y.ZZ
issue: https://github.com/OWNER/REPO/issues/NNN
version: vX.Y

# Plan: [Title]

## Decision Record
[Why this work exists -- brief rationale]

## Tasks
- [x] Task 1: Save Spec Documentation
- [ ] Task 2: [Description]
  - [Concrete step]
  - [Referenced file or module]
  - [Test expectation]
- [ ] Task 3: [Description]
  ...
- [ ] Task N: [Last implementation task]
```

When audit-task finds issues, it unchecks the task and adds indented fix items:

```markdown
- [ ] Task 6: Use OpenRouterModel for OpenRouter endpoints
  - [ ] Fix: Missing type annotation on routing_settings field (audit round N)
  - [ ] Fix: Dead import of PromptedOutput in runtime.py:3 (audit round N)
```

When handle-feedback adds items from PR reviews:

```markdown
- [ ] Fix: [description from feedback] (PR #NNN feedback from @author, feedback round N)
```

Task 1 must always be "Save Spec Documentation" (completed during shape-spec). The final task should be the last implementation task. Do not add tasks for verification gates -- the orchestrator handles those automatically.

### demo.md

```markdown
# Demo: [Title]

[Narrative intro -- what the feature is, why it matters]

## Steps

1. [Action] -- expected: [observable outcome]
2. [Action] -- expected: [observable outcome]
3. [Action] -- expected: [observable outcome]

## Results

(Appended by run-demo -- do not write this section during shaping)
```

Results are appended per run:

```markdown
### Run N -- [context] (YYYY-MM-DD HH:MM)
- Step 1: PASS|FAIL -- [brief note]
- Step 2: PASS|FAIL -- [brief note]
- Step 3: SKIPPED -- [reason]
- **Overall: PASS|FAIL**
```

### signposts.md

Created on first use by do-task or run-demo with the standard header:

```markdown
# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
will mislead future iterations. Include the exact error, command, or output
that demonstrates the problem.

---
```

Each signpost entry includes:

- **Task:** which task number
- **Status:** `unresolved` | `resolved` | `deferred` (machine-readable)
- **Problem:** what went wrong
- **Evidence:** the exact error message, command output, or code snippet
- **Tried:** what was attempted
- **Solution:** what worked (or "unresolved" if blocked)
- **Resolution:** who/what resolved it and when (e.g., "do-task round 2", "user via resolve-blockers 2026-02-08"). Omit if unresolved.
- **Files affected:** which files were involved

Signposts from run-demo additionally include:

- **Root cause:** the root cause (or best hypothesis if uncertain)

Signposts from audit-task additionally include:

- **Impact:** why this matters for future tasks

### audit-log.md

Created on first use by audit-task with the standard header:

```markdown
# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---
```

Entry formats:

```markdown
- **Task N** (round R): PASS|FAIL -- [one-line summary]
- **Demo** (run N): PASS|FAIL -- [one-line summary]
- **Spec Audit** (round N): PASS|FAIL -- [rubric summary, fix-now count]
- **Feedback** (round N): {count} items -- {valid_count} actionable, {addressed_count} addressed, {invalid_count} invalid, {deferred_count} out-of-scope
```

### audit.md

Written by audit-spec with a machine-readable header:

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
1. [Non-negotiable 1]: **PASS|FAIL** -- [evidence with file:line]
2. [Non-negotiable 2]: **PASS|FAIL** -- [evidence with file:line]

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
- [Item] -> [GitHub issue URL]
```

**Status rules:**
- `status: pass` requires: all rubric scores 5/5, all non-negotiables PASS, demo PASS, zero Fix Now items.
- `status: fail` if any of the above conditions are not met.

### standards index.yml

```yaml
folder-name:
  file-name:
    description: Brief description here
```

Rules: alphabetize folders, alphabetize files within folders, file names without `.md` extension, one-line descriptions only. The keyword `root` refers to `.md` files directly in `agent-os/standards/` (not in a subfolder).

---

## Core Commands

### shape-spec

**Purpose:** Plan the work with the user. Produce all spec artifacts and push. This is the only command where the user and agent collaborate interactively on what to build.

**Mode:** Interactive (TUI)

**Suggested model:** Strong planner with good communication skills (e.g., Opus).

**Inputs:** Issue number/URL, or the user picks from candidates.

**Outputs:** Spec folder with `spec.md`, `plan.md`, `demo.md`, `standards.md`, `references.md`, optional `visuals/`. Branch created and pushed.

**Process:**

Steps 1-11 are discussion only -- no branches, files, or git commands until Step 12.

1. **Resolve the Spec Issue.** Three paths:
   - User provides an existing issue number/URL: fetch via `gh issue view`.
   - Create a new issue: determine next available `spec_id` from GitHub issues for the target version. Create with labels `type:spec`, `status:planned`, `version:vX.Y` and set the milestone.
   - Pick the next best issue from the roadmap: if a candidate-listing script exists (e.g., `agent-os/scripts/list-candidates.py`), run it to resolve dependency chains and show only the earliest milestone. Present candidates to the user. Once chosen, fetch with `gh issue view`.

2. **Clarify Scope.** Use issue title/body as primary scope. Ask only if unclear.

3. **Gather Visuals (Optional).** Mockups, screenshots, examples, or "none".

4. **Reference Implementations (Optional).** Similar code paths in the codebase.

5. **Product Context.** If `agent-os/product/` exists, skim key files and ask about alignment.

6. **Standards.** Read `agent-os/standards/index.yml` (if it exists) and propose relevant standards.

7. **Non-Negotiables.** Define with the user. Good non-negotiables are:
   - **Specific** -- not "code should be clean" but a concrete, checkable constraint.
   - **Verifiable** -- an auditor can check pass/fail with evidence.
   - **Important** -- things that, if violated, mean the feature is fundamentally broken.

8. **Define Acceptance Criteria.** Each criterion should be observable, scoped, and complete.

9. **Demo Plan.** Write as a narrative: what the feature is, why it matters, then concrete steps to prove it works. Qualities: narrative, concise, specific, accessible, medium-agnostic. The demo plan is used by run-demo, audit-spec, and walk-spec.

10. **Task Plan.** Structure as checklist. Task 1 is always "Save Spec Documentation". Final task is the last implementation task. No task for verification gates. Think backwards from the demo: what tests guarantee each demo step succeeds?

11. **Spec Folder Name.** `YYYY-MM-DD-HHMM-{spec_id}-{feature-slug}/`.

12. **Create Branch, Save Spec Docs, Commit, Push.**
    - Create branch via `gh issue develop` and check it out.
    - Write all spec files.
    - Check off Task 1 in plan.md.
    - Commit only the spec docs.
    - Update the issue body (not a new comment) with a "Spec Summary" section.
    - Push the branch with `-u`.

13. **Stop and Handoff.** Do not start implementation. The orchestrator handles everything from here.

**Exit:** No machine-readable exit signal. The command ends with handoff instructions.

---

### do-task

**Purpose:** Pick up the next unchecked task from the plan, implement it, verify it, and commit it. One task per invocation. Fully autonomous.

**Mode:** Automated (headless)

**Suggested model:** Fast, capable implementer (e.g., Sonnet). Cost-efficiency matters -- this runs many times.

**Inputs:** Spec folder path (provided by orchestrator).

**Outputs:** Implemented task, updated plan.md checkbox, commit.

**Process:**

1. **Resolve the Spec.** Use spec folder from input. Read plan.md for metadata. Exit with `do-task-status: error` if ambiguous.

2. **Load Context.** Read spec.md (acceptance criteria, non-negotiables), plan.md (find first unchecked task), standards.md (applicable standards), signposts.md (learn from previous errors -- verify evidence before relying on claims).

3. **Identify the Task.** Find the first unchecked `[ ]` task in plan.md. If the task has indented `[ ]` fix items beneath it, address those as part of implementing the task. If no unchecked tasks remain, exit with `do-task-status: all-done`.

4. **Implement.** Execute the task as described: follow concrete steps, adhere to standards, respect non-negotiables, keep changes scoped.

5. **Run Task Gate.** Run the project's task-level verification gate (configured via `ORCH_TASK_GATE`, default `make check`). If it fails, read errors, fix, and re-run until green. If stuck after reasonable attempts, write a signpost with exact error output and exit as blocked.

6. **Check Off Task.** Change `[ ]` to `[x]` in plan.md. Check off fix items too.

7. **Signpost (If Needed).** Write to signposts.md if non-obvious issues, workarounds, or dead ends were encountered.

8. **Commit.** `git commit -m "Task N: [description]"` including plan.md and signposts.md.

9. **Exit.**

**Exit signals:**
- `do-task-status: complete` -- task done, committed.
- `do-task-status: blocked` -- stuck, signpost written with evidence.
- `do-task-status: all-done` -- no unchecked tasks remain in plan.md.
- `do-task-status: error` -- prerequisites missing or unrecoverable issue.

**Does NOT:** Run the demo, audit its own work, create branches, push, touch GitHub issues, modify spec.md, update roadmap.md, ask the user questions.

---

### audit-task

**Purpose:** Audit the most recently completed task. Lightweight, focused, fast. Fully autonomous.

**Mode:** Automated (headless)

**Suggested model:** Different model from do-task for independence (e.g., a separate model provider or reasoning-tuned model).

**Inputs:** Spec folder path (provided by orchestrator).

**Outputs:** Updated plan.md (pass or uncheck + fix items), audit-log.md entry, commit.

**Process:**

1. **Resolve the Spec.** Same as do-task.

2. **Identify the Task.** Find the most recently checked-off top-level `[x]` task (not indented fix items).

3. **Load Context.** Read spec.md, plan.md, standards.md, signposts.md (pay attention to Status field), and the implementation via `git diff HEAD~1`.

4. **Evaluate.** Check against:
   - **Task fidelity** -- Does implementation match the task description?
   - **Non-negotiable compliance** -- Any violations? These are hard failures.
   - **Standards adherence** -- Cite specific rules and file:line locations.
   - **Quality** -- Dead code, missing error handling, untested paths, naming inconsistencies, security concerns.

   Does NOT check: overall spec completeness, whether demo passes, code not changed by this task.

5. **Cross-Reference Signposts.** Before writing any fix items:
   - For resolved signposts: verify resolution is implemented in code. If working, do NOT add a fix item. If broken, add fix item with new evidence. If not implemented, reference the signpost's proposed solution.
   - For architectural constraints: verify by reading cited code. Do NOT add fix items requiring something proved infeasible. Write a new signpost with counter-evidence if you disagree.
   - For deferred signposts: skip.

6. **Verdict.**
   - **Pass:** Confirm clean, skip to audit log.
   - **Fail:** Uncheck the task (`[x]` to `[ ]`), append indented `[ ] Fix:` items with file:line references and audit round number. Reference related signposts if they exist.

7. **Signpost (If Needed).** Write if audit revealed non-obvious issues or patterns.

8. **Update Audit Log.** Append: `- **Task N** (round R): PASS|FAIL -- [summary]`.

9. **Commit.** `git commit -m "Audit: Task N -- PASS|FAIL"`.

10. **Exit.**

**Exit signals:**
- `audit-task-status: pass` -- task is clean.
- `audit-task-status: fail` -- task unchecked, fix items added.
- `audit-task-status: error` -- prerequisites missing or unrecoverable issue.

**Does NOT:** Score rubrics, check overall spec completeness, run the demo or verification gates, fix code, push, create PRs, modify spec.md.

---

### run-demo

**Purpose:** Execute the demo plan and validate it works. If it fails, investigate and route issues back to the task loop. Fully autonomous.

**Mode:** Automated (headless)

**Suggested model:** Capable implementer with good debugging skills (e.g., Sonnet).

**Inputs:** Spec folder path (provided by orchestrator).

**Outputs:** Updated demo.md (results appended), plan.md (new tasks if failures), signposts.md (if issues), audit-log.md entry, commit.

**Process:**

1. **Resolve the Spec.** Same as do-task.

2. **Load Context.** Read demo.md (steps and expected outcomes), spec.md (acceptance criteria), signposts.md (known issues).

3. **Execute Demo.** Run each step in order:
   - Execute the action.
   - Compare result against expected outcome.
   - If pass: note and continue.
   - If fail: stop and proceed to investigation.
   - If cannot execute (e.g., requires external service): note what was verified instead and why.

4. **Investigate Failures.** For each failed step:
   - Read error output.
   - Check test coverage -- if tests pass but demo fails, identify the test gap.
   - Trace root cause through the code.
   - Write a signpost with `Status: unresolved`.
   - Add tasks to plan.md: if test gap, add a task for tests first then a fix task; if code is wrong, add a fix task.

5. **Record Results.** Append to demo.md under `## Results`.

6. **Update Audit Log.** Append: `- **Demo** (run N): PASS|FAIL -- [summary]`.

7. **Commit.** Include demo.md, audit-log.md, signposts.md, plan.md (only modified files).

8. **Exit.**

**Exit signals:**
- `run-demo-status: pass` -- all steps passed.
- `run-demo-status: fail` -- one or more steps failed, tasks added to plan.md.
- `run-demo-status: error` -- prerequisites missing or unrecoverable issue.

**Does NOT:** Fix code itself, modify spec.md, push, score rubrics, skip investigation.

---

### audit-spec

**Purpose:** Bird's-eye audit of the full implementation after all tasks and demo pass. Score rubrics, check non-negotiables, verify standards adherence, detect regressions. Fully autonomous.

**Mode:** Automated (headless)

**Suggested model:** Strong reasoner, different from do-task (e.g., a reasoning-tuned model from a different provider). Quality matters more than speed.

**Inputs:** Spec folder path (provided by orchestrator).

**Outputs:** audit.md (with machine-readable status header), plan.md (Fix Now items), audit-log.md entry, GitHub issue comment, commit.

**Process:**

1. **Resolve the Spec.** Same as do-task.

2. **Load Context.** Read all spec files: spec.md, plan.md, standards.md, references.md, demo.md, signposts.md, audit-log.md, implementation files and tests.

3. **Perform Audit.** Seven dimensions:

   **3a: Rubric Scores (1-5).** Score each:
   - **Performance** -- Efficient? No unnecessary computation, I/O, or memory usage?
   - **Intent** -- Matches spec goals? Solves the right problem?
   - **Completion** -- All acceptance criteria met? Gaps?
   - **Security** -- No injection, hardcoded credentials, unsafe deserialization, OWASP concerns?
   - **Stability** -- Proper error handling, no silent failures, edge case resilience?

   **3b: Non-Negotiable Compliance.** For each non-negotiable: explicit PASS or FAIL with evidence (file:line, code snippet, command output). Failures are automatic audit failures regardless of scores.

   **3c: Standards Adherence.** Check all standards across the full implementation (not just per-task diffs). For each violation: cite rule, file:line, severity (High/Medium/Low).

   **3d: Demo Status.** Check demo.md results: did it pass? Results convincing? Steps skipped with reasonable justification? If demo was not run, flag as Fix Now.

   **3e: Signpost Cross-Reference.** Before flagging Fix Now items:
   - Resolved signposts: verify resolution in code. Do NOT re-open without new evidence.
   - Architectural constraints: do NOT require infeasible approaches.
   - Deferred signposts: do not promote without new evidence.
   - Unresolved signposts: fair game for Fix Now items.

   **3f: Regression Check.** Review audit-log.md for patterns: tasks that regressed, recurring issues, systemic problems.

   **3g: Cross-Cutting Concerns.** Consistency, architectural coherence, test coverage gaps spanning multiple tasks.

4. **Categorize Action Items.**
   - High/Medium severity -> **Fix Now**: append as `[ ]` entries at bottom of plan.md Tasks section with file:line citations.
   - Low severity -> **Defer**: create a GitHub issue with `type:spec`, `status:planned`, `version:vX.Y` labels. Record the issue URL in audit.md.
   - Do NOT edit roadmap.md during audit.

5. **Write audit.md.** Machine-readable header (`status:`, `fix_now_count:`) followed by the full report.

6. **Update Audit Log.** Append: `- **Spec Audit** (round N): PASS|FAIL -- [rubric summary, fix-now count]`.

7. **Report to GitHub.** Update the existing "Spec Progress" comment on the spec issue (create once if missing).

8. **Commit.** `git commit -m "Spec audit round N: PASS|FAIL"`.

9. **Exit.** The exit signal is the `status:` field in audit.md:
   - `status: pass` -> orchestrator proceeds to notify human for walk-spec.
   - `status: fail` -> orchestrator loops back to do-task.

**Does NOT:** Fix anything, run the demo itself, push, create PRs, touch roadmap.md, modify spec.md.

**Success criteria:** All rubric scores 5/5, all non-negotiables pass, demo passes, zero Fix Now items.

---

### walk-spec

**Purpose:** Human validation checkpoint. Walks user through interactive demo, submits PR, updates roadmap.

**Mode:** Interactive (TUI)

**Suggested model:** Strong communicator (e.g., Opus). Needs excellent interactive skills.

**Inputs:** Issue number/URL or spec_id.

**Outputs:** PR created, roadmap updated, branch pushed.

**Prerequisites:** All tasks checked in plan.md, audit passes (`status: pass` in audit.md), demo passed (results in demo.md), clean working tree.

**Process:**

1. **Resolve the Spec.** Use issue from user input, plan.md metadata, or list spec folders and ask.

2. **Gather Context (Autonomous).** Read all spec files and implementation files. Do not ask the user for summaries.

3. **Run Verification Gate.** Run the project's spec gate. If fails, stop and report.

4. **Implementation Summary.** Present:
   - Key changes with file:line references.
   - How each acceptance criterion was met (cite evidence).
   - Non-negotiable compliance (explicit pass/fail from audit.md).
   - Audit scores.
   - Demo status.
   - Deferred items (confirm user accepts them).

5. **Interactive Demo Walkthrough.** For each step:
   - Explain what you are about to do and why.
   - Execute it (or give instructions for steps requiring user interaction).
   - Show the result.
   - Explain what the result proves.
   - Confirm before moving on.
   - If a step fails: stop, investigate, present findings, discuss options (fix now, accept as-is, abort).

6. **Prepare PR.** Create with `gh pr create`:
   - Title: `{spec_id} {short title}`.
   - Body: Summary, Spec section (issue, audit status, non-negotiables, demo), Deferred section.

7. **Update Roadmap.** If the spec has an entry in `agent-os/product/roadmap.md`, mark it as complete. Commit on the branch.

8. **Evaluate Standards Evolution.** Skim signposts.md and audit-log.md for patterns. Recommend `/discover-standards` if warranted.

9. **Final Push and Report.** Push branch, update "Spec Progress" comment on the issue with PR link, report PR URL and follow-ups.

**Does NOT:** Implement or fix code, run audit-spec, create branches, make implementation decisions without user input.

---

## The Orchestrator

`agent-os/scripts/orchestrate.sh` -- the automated backbone of the workflow. It sequences agent invocations, runs verification gates, detects staleness, and routes signals. The intelligence lives in the agents; the orchestrator only does sequencing, gating, and routing.

### Usage

```bash
./agent-os/scripts/orchestrate.sh <spec-folder>
./agent-os/scripts/orchestrate.sh <spec-folder> --config orchestrate.conf
```

The spec folder must contain `spec.md` and `plan.md` (output of shape-spec).

### Configuration

Configuration via environment variables, config file (`--config`), or defaults.

**Per-command CLI and model:**

The orchestrator supports configuring which CLI tool and model to use for each command. This enables model independence (different providers for implementation vs. auditing). The defaults reference specific tools and models, but you can substitute any compatible agent CLI and model:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCH_CLI` | `claude -p --dangerously-skip-permissions` | Fallback CLI for implementation commands |
| `ORCH_DO_CLI` | `$ORCH_CLI` | CLI for do-task |
| `ORCH_AUDIT_CLI` | `codex exec --yolo` | CLI for audit-task |
| `ORCH_DEMO_CLI` | `$ORCH_CLI` | CLI for run-demo |
| `ORCH_SPEC_CLI` | `codex exec --yolo` | CLI for audit-spec |
| `ORCH_DO_MODEL` | `sonnet` | Model for do-task |
| `ORCH_AUDIT_MODEL` | `gpt-5.3-codex` | Model for audit-task |
| `ORCH_DEMO_MODEL` | `sonnet` | Model for run-demo |
| `ORCH_SPEC_MODEL` | `gpt-5.3-codex` | Model for audit-spec |

> **Note:** The specific model names and CLI tools in the defaults will evolve as new models are released. The key principle is to use different model providers for implementation vs. auditing (to avoid "grading your own homework"). Adjust these to match whatever models are current and available to you.

**Gates and limits:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCH_TASK_GATE` | `make check` | Task-level verification command (any shell command that returns 0 on success) |
| `ORCH_SPEC_GATE` | `make all` | Spec-level verification command (any shell command that returns 0 on success) |
| `ORCH_MAX_CYCLES` | `10` | Safety limit on full cycles (staleness detector is primary) |
| `ORCH_COMMANDS_DIR` | `.claude/commands/agent-os` | Path to command markdown files |
| `ORCH_AGENT_TIMEOUT` | `1800` | Per-agent invocation timeout in seconds |
| `ORCH_MAX_TASK_RETRIES` | `5` | Max attempts for a single task before aborting |
| `ORCH_STALE_LIMIT` | `3` | Cycles with unchanged plan.md before aborting |

A config file is sourced as a bash file, so it can set any of these variables. Example config file:

```bash
# orchestrate.conf -- example for a Node.js project
ORCH_TASK_GATE="npm run lint && npm test"
ORCH_SPEC_GATE="npm run test:all"
ORCH_DO_MODEL="sonnet"
ORCH_AUDIT_MODEL="o3"
ORCH_AGENT_TIMEOUT=2400
```

### Phases

The orchestrator runs in cycles, each with four phases:

**Phase 1: Task Loop.** For each unchecked task:
1. Invoke `do-task` with the configured CLI and model.
2. Check the spec.md immutability guard.
3. Extract the `do-task-status` exit signal.
4. Run the task gate. If it fails, re-invoke do-task with the gate error output. Retry up to `MAX_GATE_RETRIES` (hardcoded to 3) times.
5. Invoke `audit-task` with the configured CLI and model.
6. Check the spec.md immutability guard.
7. Extract the `audit-task-status` exit signal.
8. Self-heal: if audit passes but the task checkbox was not persisted, the orchestrator checks it off and also checks off any orphaned fix items under it.

Inner-loop retry limit: if the same task label appears consecutively, increment a counter. After `ORCH_MAX_TASK_RETRIES` attempts, abort.

**Phase 2: Spec Gate.** Run the spec gate. If it fails, invoke `do-task` with the gate error output and restart the cycle.

**Phase 3: Demo.** Invoke `run-demo`. If it fails (signal: `fail`), new tasks were added to plan.md; restart the cycle. If it passes, proceed.

**Phase 4: Spec Audit.** Invoke `audit-spec`. Verify audit.md was actually written/updated (check mtime before and after). Read `status:` from audit.md first line. If `pass`, break the loop and exit successfully. If `fail`, restart the cycle.

### Signal Extraction

Agents write their exit signal to a status file (`$SPEC_FOLDER/.agent-status`) as instructed in the prompt. The orchestrator uses a two-tier extraction:

1. **Primary:** Read the signal from the `.agent-status` file using regex `{prefix}: \K\w[\w-]*`.
2. **Fallback:** Grep the agent's stdout output for the same pattern (fragile but backwards-compatible).

The status file is cleared before each agent invocation.

### Exit Signal Handling

**do-task signals:**
| Signal | Orchestrator Action |
|--------|-------------------|
| `complete` | Continue to gate |
| `all-done` | Break task loop |
| `blocked` | Abort with "Human intervention needed. See signposts.md." |
| `error` | Abort, print last 20 lines of output |
| (empty) | Warn "no signal detected", continue (gate will verify) |
| (unrecognized) | Warn, continue |

**audit-task signals:**
| Signal | Orchestrator Action |
|--------|-------------------|
| `pass` | Continue; self-heal checkbox if needed |
| `fail` | Continue (fix items added, loop picks up unchecked task) |
| `error` | Abort, print last 20 lines |
| (empty) | Warn, continue |
| (unrecognized) | Warn, continue |

**run-demo signals:**
| Signal | Orchestrator Action |
|--------|-------------------|
| `pass` | Proceed to spec audit |
| `fail` | Restart cycle (new tasks added) |
| `error` | Abort, print last 20 lines |
| (empty) | Abort, print last 20 lines |
| (unrecognized) | Warn, continue |

**audit-spec:** Uses `status:` field from audit.md first line (not stdout signal).
| Status | Orchestrator Action |
|--------|-------------------|
| `pass` | Exit successfully |
| `fail` | Restart cycle (Fix Now items added) |
| (other/missing) | Abort |

### Staleness Detection

The orchestrator detects when agents are not making progress:

- At the start of each cycle, snapshot `plan.md` (MD5 hash).
- If the snapshot is identical to the previous cycle, increment `stale_count`.
- If `stale_count >= ORCH_STALE_LIMIT`, abort: "Stale -- plan.md unchanged for N cycles."
- If the snapshot changes, reset `stale_count` to 0.
- Staleness detection is only active after tasks have existed (the `had_tasks` flag). When all tasks were already done at startup, plan.md not changing is expected.

### Concurrency Lock

The orchestrator uses `flock` on file descriptor 9 to prevent two instances from running on the same spec folder simultaneously:

```bash
LOCK_FILE="$SPEC_FOLDER/.orchestrate.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    fail "Another orchestrator is already running on $SPEC_FOLDER"
    exit 1
fi
```

The lock is released automatically when the script exits.

### Spec Immutability Guard

At startup, the orchestrator snapshots spec.md (MD5 hash + file backup). After every agent invocation, it checks the hash. If spec.md was modified:

1. Revert spec.md from the backup.
2. `git add` the reverted file.
3. `git commit --amend --no-edit` to fix the commit.
4. Print a warning: "Agent modified spec.md -- reverting (immutability contract)".

This is a self-healing mechanism -- the orchestrator repairs the violation rather than aborting.

### Task Gate Retry Logic

When the task gate fails after a do-task invocation:

1. Re-invoke do-task with extra context: the gate failure output, instructions to fix errors and re-run the gate.
2. If do-task returns `blocked` or `error` during the fix attempt, abort.
3. Re-run the gate.
4. Repeat up to `MAX_GATE_RETRIES` (3) times.
5. If the gate still fails after 3 attempts, abort with the gate output.

### Self-Heal: Checkbox Bookkeeping

After audit-task passes, the orchestrator checks if the task checkbox was actually persisted in plan.md. If the task is still unchecked:

1. Use `awk` to check off the task.
2. Also check off any orphaned fix items under that task.
3. `git add` plan.md and amend the commit (or create a new "bookkeeping" commit).

### Agent Invocation

The `invoke_agent` function handles running agents:

1. Read the command markdown file from `ORCH_COMMANDS_DIR`.
2. Append runtime context: spec folder path, extra context (e.g., gate errors), and instructions to write the exit signal to `.agent-status`.
3. Build the CLI command with the model flag.
4. Run as a background process with `timeout` for interruptibility.
5. For Codex-style agents: use `-o` flag to capture last message to a file.
6. For Claude-style agents: capture stdout to a temp file.
7. If timeout (exit code 124): report timeout, return empty output.
8. Store output in `AGENT_OUTPUT` global variable.

### Progress Display

The orchestrator displays a live progress UI:

- Spinner with phase name, model, and elapsed time.
- Green checkmark for success, red X for failure.
- Annotations for each phase result (e.g., "task completed", "issues found").
- Cycle headers with remaining task count.
- Warning indicators for retries, staleness, and missing signals.
- Total elapsed time at completion.
- Victory fanfare (audio) on success (best-effort, platform-adaptive).

### Cleanup

The orchestrator traps EXIT, INT, and TERM signals to clean up:

- Kill the timer process.
- Kill the agent process (TERM first, KILL after 5 seconds).
- Remove temp files (status file, spec backup, agent output file).
- Clear the spinner line.

### Completion

On success:
1. Play victory fanfare.
2. Clean up `.agent-status` file.
3. Print total elapsed time.
4. Print next step: "run `/walk-spec` for interactive demo + PR".

---

## Feedback and Blocker Commands

### handle-feedback

**Purpose:** Pull PR review comments and automated analysis feedback, evaluate correctness, and route valid feedback into the spec workflow as tasks. Interactive.

**Mode:** Interactive (TUI)

**Suggested model:** Strong reasoner with good judgment (e.g., Opus).

**When to use:** After PR creation (via walk-spec) when review comments arrive, when automated analysis agents leave comments, when community reviewers provide feedback, or periodically during long reviews.

**Prerequisites:** Spec folder with spec.md and plan.md, an existing PR, comments or check annotations to process.

**Process:**

1. **Resolve Spec and PR.** Find the PR via `gh pr list --head <branch-name>` or user input.

2. **Fetch Feedback.** Four sources:
   - PR review comments (inline): `gh api repos/{owner}/{repo}/pulls/{pr_number}/comments`
   - PR review bodies (top-level): `gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews`
   - Issue-style comments: `gh pr view {pr_number} --comments --json comments`
   - Check run annotations: `gh pr checks` and `gh api repos/{owner}/{repo}/check-runs/{id}/annotations`

   Parse each into: ID, Source (author, review type), File:line, Body, Is bot.

3. **Load Context.** Read spec.md, plan.md, signposts.md, standards.md, audit.md.

4. **Triage Each Item.** For each piece of feedback:
   - Read the relevant code with surrounding context.
   - Evaluate the claim's correctness.
   - Check signposts.md for existing resolutions.
   - Classify: `valid-actionable`, `valid-addressed`, `invalid`, `style-preference`, `out-of-scope`, `duplicate`.
   - Write rationale with file:line evidence.

5. **Present Triage to User.** Grouped by classification. User can override classifications, edit replies, choose actions.

6. **Execute Approved Actions.**
   - **valid-actionable:** Add `[ ] Fix:` items to plan.md. Write signpost if non-obvious. Uncheck affected task.
   - **valid-addressed:** Post reply comment explaining where/how handled, with file:line and signpost references.
   - **invalid:** Post polite reply with evidence. If readability gap, reclassify as style-preference.
   - **style-preference:** Acknowledge in reply. If user wants to adopt, add fix item. If multiple reviewers raise same point, recommend `/discover-standards`.
   - **out-of-scope:** Create GitHub issue (`type:spec`, `status:planned`), post reply referencing new issue.

7. **Update Audit Log.** Append feedback round entry.

8. **Commit and Push.**

**Exit signals:**
- `handle-feedback-status: resolved` -- all feedback handled, replies posted.
- `handle-feedback-status: tasks-added` -- fix items added, orchestrator needs re-run.
- `handle-feedback-status: no-feedback` -- no comments found.
- `handle-feedback-status: error` -- prerequisites missing or unrecoverable.

**Does NOT:** Fix code, merge PR, modify spec.md, run tests/gates, make triage decisions autonomously, post replies without user approval.

---

### resolve-blockers

**Purpose:** Investigate blockers that halted the orchestrator, propose solutions, and reconcile spec artifacts. Interactive.

**Mode:** Interactive (TUI)

**Suggested model:** Strong reasoner with good interactive skills (e.g., Opus).

**When to use:**
- Orchestrator halts with "Human intervention needed. See signposts.md."
- Orchestrator halts with "Task stuck after N attempts."
- Orchestrator halts with "Stale -- plan.md unchanged."
- Audit contradictions (e.g., auditor ignoring resolved signposts).
- plan.md fix items conflicting with signpost resolutions.

**Prerequisites:** Spec folder with spec.md, plan.md, signposts.md. At least one blocker.

**Process:**

1. **Resolve the Spec.** Same as other commands.

2. **Investigate.** Read all spec artifacts. Scan for:
   - Unresolved signposts (Status: unresolved or no Status field).
   - Contradictory fix items (conflict with resolved signposts).
   - Stuck tasks (repeated FAIL entries in audit-log.md).
   - Architectural constraints (documented infeasibility).
   - Spec/reality mismatches (acceptance criteria requiring the impossible).
   - Verify claims by reading code at cited file:line locations.

3. **Present Blocker Report.** For each blocker: source, root cause, what's been tried. Present 2-3 resolution options ranked by recommendation:
   - **Option A (Recommended):** What, Why, Changes, Risk.
   - **Option B:** Alternative approach.
   - **Option C: Defer to future spec** -- create GitHub issue, mark signpost as deferred.

4. **Reconcile Artifacts.** Based on user decisions:
   - **Update signposts.md:** Set Status to `resolved` or `deferred`, add Resolution field.
   - **Update plan.md:** Remove contradictory fix items, add new ones if needed, re-scope tasks.
   - **Update spec.md (ONLY with explicit user approval):** Present exact before/after diff first. This is the nuclear option -- prefer adjusting plan.md or deferring.
   - **For deferred blockers:** Create GitHub issue, update signpost Status to `deferred`, remove dependent fix items, record issue URL.

5. **Verify Consistency.** After updates, check:
   - No unchecked fix items contradicting resolved signposts.
   - No checked tasks with unresolved fix items beneath them.
   - All signposts have a Status field.
   - plan.md task count is expected.

6. **Run Gate (If Code Changes).** Run the task gate. If non-trivial fix needed, add task to plan.md.

7. **Commit.**

8. **Advise Next Steps.** Re-run orchestrator, note spec.md changes, list deferred issue URLs.

**Exit signals:**
- `resolve-blockers-status: resolved` -- all blockers resolved, orchestrator can resume.
- `resolve-blockers-status: deferred` -- some blockers deferred to future specs.
- `resolve-blockers-status: partial` -- some resolved, others need more investigation.
- `resolve-blockers-status: no-blockers` -- no blockers found.
- `resolve-blockers-status: error` -- prerequisites missing or unrecoverable.

**Does NOT:** Implement code fixes, run demo, audit implementation, push or create PRs, make decisions autonomously.

---

## Supporting Commands

### plan-product

**Purpose:** Establish foundational product documentation through interactive conversation. This is typically one of the first things you run when adopting Agent OS for a new project.

**Mode:** Interactive (TUI)

**Outputs:** `agent-os/product/mission.md`, `agent-os/product/roadmap.md`, `agent-os/product/tech-stack.md`.

**Process:**

1. Check for existing product docs. If any exist, offer: start fresh, update specific files, or cancel.
2. Gather product vision (for mission.md): what problem it solves, who it's for, what makes it unique.
3. Gather roadmap (for roadmap.md): MVP features, post-launch features.
4. Establish tech stack (for tech-stack.md): check if `agent-os/standards/global/tech-stack.md` exists first; if so, offer to reuse. Otherwise, ask about frontend, backend, database, other.
5. Generate files.
6. Confirm completion.

Product docs are read by shape-spec during planning for context alignment.

---

### inject-standards

**Purpose:** Inject relevant standards into the current context, formatted for the situation.

**Mode:** Interactive (TUI)

**Usage modes:**
- **Auto-Suggest** (`/inject-standards`): Analyzes context, suggests relevant standards.
- **Explicit** (`/inject-standards api`, `/inject-standards api/response-format`): Directly injects specified standards.

**Scenarios:**
1. **Conversation** -- Read standards into chat (full content).
2. **Creating a Skill** -- Output as `@` file references or full content (user chooses).
3. **Shaping/Planning** -- Output as `@` file references or full content (user chooses).

**Process for auto-suggest:**
1. Detect context scenario (plan mode, skill creation, or conversation). Ask if uncertain.
2. Read `agent-os/standards/index.yml`.
3. Analyze work context.
4. Match and suggest 2-5 standards.
5. Inject based on scenario.
6. Surface related skills (conversation scenario only).

**Explicit mode arguments:**
- Folder name (`api`) -> all `.md` files in `agent-os/standards/api/`.
- Folder/file (`api/response-format`) -> specific file.
- `root` -> all `.md` files directly in `agent-os/standards/` (reserved keyword, not an actual folder).
- `root/naming` -> specific file in standards root.

This command is called internally by shape-spec during planning.

---

### discover-standards

**Purpose:** Extract tribal knowledge from the codebase into concise, documented standards. This is how you build your standards library over time.

**Mode:** Interactive (TUI)

**Process:**

1. **Determine Focus Area.** Identify 3-5 major areas in the codebase. User picks one.
2. **Analyze and Present Findings.** Read 5-10 representative files. Look for patterns that are unusual, opinionated, tribal, or consistent. Present to user for selection.
3. **Ask Why, Then Draft Each Standard.** For each selected standard, complete the full loop: ask 1-2 clarifying "why" questions, draft the standard incorporating answers, confirm, create file. One standard at a time.
4. **Create Standard File.** Place in appropriate folder under `agent-os/standards/`. Append to existing file if related standard exists.
5. **Update the Index.** Scan for new files, propose descriptions, update `agent-os/standards/index.yml`.
6. **Offer to Continue.** Offer to discover standards in another area.

**Writing guidelines:** Lead with the rule, use code examples, skip the obvious, one standard per concept, bullet points over paragraphs. Standards are injected into AI context windows -- every word costs tokens.

---

### index-standards

**Purpose:** Rebuild and maintain the standards index file (`agent-os/standards/index.yml`).

**Mode:** Interactive (TUI)

**Process:**

1. Scan all `.md` files in `agent-os/standards/` and subfolders. Files in the root use "root" as the folder name.
2. Load existing index.
3. Identify changes: new files, deleted files, existing files.
4. For new files: read the file, propose a one-sentence description, confirm with user.
5. For deleted files: remove stale entries automatically.
6. Write updated index (alphabetized by folder, then filename, no `.md` extensions).
7. Report results.

The index enables `/inject-standards` to suggest relevant standards without reading all files. Run after manually creating/deleting standards, or if suggestions seem out of sync. `/discover-standards` runs this automatically as its final step.

---

### sync-roadmap

**Purpose:** Sync `agent-os/product/roadmap.md` with GitHub issues labeled `type:spec`.

**Mode:** Interactive (TUI)

**Process:**

1. **Load Sources.** Parse roadmap.md for spec items (spec_id, title, status, version, depends_on). Fetch GitHub issues with label `type:spec`.
2. **Compare and Classify.** For each spec_id: match, roadmap-only, GitHub-only, or conflict.
3. **Resolve Conflicts.** Ask user with recommended default (usually GitHub).
4. **Apply Sync Actions.**
   - Roadmap-only: create GitHub issue (verify spec_id not already used).
   - GitHub-only: add roadmap entry.
   - Match: ensure dependencies aligned.
5. **Dependency Alignment.** Sync blocked-by relationships between GitHub and roadmap depends_on.
6. **Report Summary.**

GitHub is the source of truth for spec IDs.

---

## Deprecated Commands

`/do-spec` and `/fix-spec` are deprecated and redirect to `/do-task`.

---

## Verification Gates

Two tiers of verification, used at different points:

| Gate | Default Command | Typical Contents | When Used |
|------|----------------|------------------|-----------|
| Task gate | `make check` (configurable via `ORCH_TASK_GATE`) | Fast checks: format, lint, typecheck, unit tests | After each task implementation |
| Spec gate | `make all` (configurable via `ORCH_SPEC_GATE`) | Thorough checks: everything in task gate + integration tests, quality checks | After all tasks complete, before demo |

The gate commands are fully configurable. The defaults (`make check` / `make all`) are just conventions -- you can use any shell command that returns exit code 0 on success. See [Adapting to Your Project](#adapting-to-your-project) for examples with other tech stacks.

**Belt-and-suspenders:** The agent runs the gate internally (do-task runs the task gate), and the orchestrator re-runs it as a hard external gate. This catches cases where the agent claims success but the gate actually fails.

---

## The Signpost System

Signposts are the institutional memory of a spec implementation. They capture problems encountered, solutions found, and architectural constraints discovered, with mandatory evidence.

### Purpose

- Prevent agents from repeating known failures.
- Communicate constraints between agents (do-task to audit-task, across cycles).
- Provide evidence for resolution decisions.
- Enable resolve-blockers to diagnose stuck loops.

### Rules

1. **Every signpost must include evidence.** A conclusion without proof misleads future iterations. Include the exact error, command, or output that demonstrates the problem.
2. **Status is machine-readable.** Three values: `unresolved`, `resolved`, `deferred`.
3. **Signposts are append-only** (new entries only). However, the Status field can be updated (e.g., from `unresolved` to `resolved`).
4. **Do not write signposts for routine work.** Only when future tasks or iterations would benefit.

### How Each Command Uses Signposts

| Command | Reads | Writes | Updates Status |
|---------|-------|--------|----------------|
| do-task | Yes (verify evidence before trusting) | Yes (if non-obvious issues) | No |
| audit-task | Yes (cross-reference before fix items) | Yes (if audit reveals non-obvious issues) | No |
| run-demo | Yes (check for known issues) | Yes (always for failures, Status: unresolved) | No |
| audit-spec | Yes (cross-reference before Fix Now items) | No | No |
| resolve-blockers | Yes (investigate blockers) | Yes (new entries or missing ones) | Yes (resolved/deferred) |
| handle-feedback | Yes (check for existing resolutions) | Yes (if feedback reveals non-obvious issues) | No |

### Cross-Reference Protocol

Before adding fix items, audit-task and audit-spec must:

1. Check resolved signposts: verify resolution is implemented in code. If working, do NOT re-open. If broken, add fix item with NEW evidence.
2. Check architectural constraints: do NOT require infeasible approaches. Propose alternatives or defer.
3. Check deferred signposts: skip unless new blocking evidence.
4. Unresolved signposts: fair game for fix items.

---

## The Audit System

Two levels of auditing serve different purposes:

### Task-Level Audit (audit-task)

- **Scope:** Most recently completed task only.
- **Focus:** Task fidelity, non-negotiable compliance, standards adherence, code quality.
- **Does NOT check:** Overall spec completeness, demo pass, code not changed by this task.
- **Output:** PASS or FAIL with fix items. Audit-log entry.
- **Frequency:** After every task implementation.

### Spec-Level Audit (audit-spec)

- **Scope:** Full implementation across all tasks.
- **Focus:** Five rubric scores (1-5), non-negotiable compliance, standards adherence, demo status, regression check, cross-cutting concerns.
- **Output:** audit.md with machine-readable status header. Fix Now items in plan.md. Deferred items as GitHub issues. Audit-log entry. GitHub issue comment.
- **Frequency:** After all tasks complete and demo passes.

### Rubric Dimensions (Spec Audit)

| Dimension | Checks |
|-----------|--------|
| Performance | Efficient implementation, no unnecessary computation/I/O/memory |
| Intent | Matches spec goals, solves the right problem |
| Completion | All acceptance criteria met, no gaps |
| Security | No injection, hardcoded credentials, unsafe deserialization, OWASP concerns |
| Stability | Proper error handling, no silent failures, edge case resilience |

### Pass Criteria (Spec Audit)

All of the following must be true:
- All rubric scores: 5/5.
- All non-negotiables: PASS.
- Demo: PASS.
- Fix Now items: 0.

### Model Independence

A core design principle: implementation and auditing use different AI models/providers to avoid "grading your own homework." The orchestrator's default configuration uses separate providers for implementation and auditing, but you should configure whatever models work best for your needs -- the key constraint is that the implementer and auditor should be different.

---

## GitHub Issues and Spec IDs

GitHub is the source of truth for spec IDs.

When creating a new spec:
- Check GitHub for the next available `spec_id` in the target version.
- Use labels: `type:spec`, `status:planned`, `version:vX.Y`.
- Set the milestone.

Spec ID format: `sX.Y.ZZ` (e.g., `s0.1.05`).

To align local roadmap with GitHub: run `/sync-roadmap`.

---

## Branching and PRs

- `shape-spec` creates the branch via `gh issue develop` and pushes it.
- All implementation happens on this branch with one commit per task.
- `walk-spec` submits the PR and pushes final changes.
- `handle-feedback` pushes feedback-related commits to the PR branch.

PR body format:

```markdown
## Summary
- [Key change 1]
- [Key change 2]
- [Key change 3]

## Spec
- Issue: #NNN
- Audit: {status} ({rubric scores})
- Non-negotiables: all passed
- Demo: passed

## Deferred
- [Item] -> #NNN
```

---

## Configuration Reference

### Environment Variables (Orchestrator)

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCH_CLI` | `claude -p --dangerously-skip-permissions` | Fallback CLI for implementation commands |
| `ORCH_DO_CLI` | `$ORCH_CLI` | CLI for do-task |
| `ORCH_AUDIT_CLI` | `codex exec --yolo` | CLI for audit-task |
| `ORCH_DEMO_CLI` | `$ORCH_CLI` | CLI for run-demo |
| `ORCH_SPEC_CLI` | `codex exec --yolo` | CLI for audit-spec |
| `ORCH_DO_MODEL` | `sonnet` | Model for do-task |
| `ORCH_AUDIT_MODEL` | `gpt-5.3-codex` | Model for audit-task |
| `ORCH_DEMO_MODEL` | `sonnet` | Model for run-demo |
| `ORCH_SPEC_MODEL` | `gpt-5.3-codex` | Model for audit-spec |
| `ORCH_TASK_GATE` | `make check` | Task-level verification command |
| `ORCH_SPEC_GATE` | `make all` | Spec-level verification command |
| `ORCH_MAX_CYCLES` | `10` | Safety limit on full cycles |
| `ORCH_COMMANDS_DIR` | `.claude/commands/agent-os` | Path to command markdown files |
| `ORCH_AGENT_TIMEOUT` | `1800` | Per-agent invocation timeout (seconds) |
| `ORCH_MAX_TASK_RETRIES` | `5` | Max attempts for a single task |
| `ORCH_STALE_LIMIT` | `3` | Cycles with unchanged plan.md before abort |

### Hardcoded Constants (Orchestrator)

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_GATE_RETRIES` | `3` | Max task gate retry attempts per task |

### Config File

Pass via `--config`:

```bash
./agent-os/scripts/orchestrate.sh <spec-folder> --config my-config.conf
```

The config file is sourced as bash, so any `ORCH_*` variable can be set.

---

## Adapting to Your Project

Agent OS is designed to be project-agnostic. Here are the main customization points:

### Verification Gates

The most important thing to configure. Replace the default `make check` / `make all` with whatever commands validate your project:

| Tech Stack | Task Gate (`ORCH_TASK_GATE`) | Spec Gate (`ORCH_SPEC_GATE`) |
|------------|------------------------------|------------------------------|
| Python + make | `make check` | `make all` |
| Node.js | `npm run lint && npm test` | `npm run test:all` |
| Rust | `cargo clippy && cargo test` | `cargo test --all-features` |
| Go | `go vet ./... && go test ./...` | `go test -race -count=1 ./...` |
| Ruby | `bundle exec rubocop && bundle exec rspec --tag ~slow` | `bundle exec rspec` |
| Java/Maven | `mvn checkstyle:check test` | `mvn verify` |
| Multi-language | `./scripts/check.sh` | `./scripts/check-all.sh` |

The only requirement is that the command returns exit code 0 on success and non-zero on failure.

### Agent Models

Configure which AI models handle each role. The key principle is model independence -- use different providers or models for implementation vs. auditing:

```bash
# Example: Use Claude for implementation, a different provider for auditing
ORCH_DO_MODEL="sonnet"
ORCH_AUDIT_MODEL="o3"

# Example: Use the same provider but different capability tiers
ORCH_DO_MODEL="sonnet"
ORCH_AUDIT_MODEL="opus"
```

### Standards

Standards are entirely project-specific. Start with `/discover-standards` to extract your existing conventions, then add to them over time. Common standard categories:

- **Language-specific:** naming conventions, import ordering, error handling patterns
- **Framework-specific:** component structure, routing patterns, state management
- **Project-specific:** API formats, database conventions, testing strategies

### Product Documentation

The `agent-os/product/` directory is optional but recommended. It gives shape-spec context about your product when planning features. Create it with `/plan-product` or by writing the files directly.

### Candidate Listing Script

The shape-spec command can optionally use a script at `agent-os/scripts/list-candidates.py` to resolve dependency chains and suggest which spec to work on next. This script is project-specific -- write one that reads your GitHub issues and roadmap to determine the next best spec to implement.

### Directory Layout

The default directory structure can be adjusted by setting `ORCH_COMMANDS_DIR` for command files. The standard layout is:

```
.claude/commands/agent-os/    -- command definitions
agent-os/
  scripts/                    -- orchestrator and supporting scripts
  standards/                  -- project coding standards
  product/                    -- product documentation
  specs/                      -- spec folders (created per feature)
```

---

## Design Principles

### Immutable Contract vs. Mutable Work Tracker

`spec.md` is the immutable contract: acceptance criteria and non-negotiables are set during shaping and never changed by automated commands. `plan.md` is the mutable work tracker: tasks are checked off, fix items are added by audits, new tasks are added by demos and spec audits.

The only way to modify spec.md is through resolve-blockers with explicit user approval after presenting the exact diff. This is the "nuclear option."

### Different Models for Implementation vs. Audit

Using the same model to both write and review code is like grading your own homework. The orchestrator is designed to use different model providers for implementation and auditing to ensure independent review. Configure this through the `ORCH_*_MODEL` and `ORCH_*_CLI` variables.

### Belt-and-Suspenders Verification

Agents run verification gates internally (do-task runs the task gate), and the orchestrator re-runs them externally as hard gates. This catches cases where agents claim success but the gate actually fails.

### Staleness Detection Over Arbitrary Limits

Instead of a fixed iteration cap as the primary control, the orchestrator detects when agents are not making progress (plan.md unchanged across cycles). The max cycles limit is a safety net, not the primary stop condition.

### Evidence-Based Signposts

Signposts require evidence -- not just conclusions. "The API fails" is not a signpost; "The API returns 500 with error 'missing field: routing_mode' when called with config X" is. This prevents misinformation from propagating across agent invocations.

### Audit Cross-Reference Before Fix Items

Auditors must check signposts.md before adding fix items. This prevents the "audit-task undoes resolved work" anti-pattern where an auditor re-opens an issue that was already solved, causing a ping-pong loop between do-task and audit-task.

### Self-Healing Over Aborting

When the orchestrator detects a problem it can fix (spec.md modified, checkbox not persisted), it self-heals rather than aborting. This keeps the automated loop running without human intervention for recoverable issues.

### Standards as Long-Term Memory

Standards in `agent-os/standards/` are long-term institutional knowledge that persists across specs. Signposts and audit logs are per-spec artifacts. walk-spec evaluates whether per-spec learnings should be promoted to standards via `/discover-standards`.

### Human-in-the-Loop at the Boundaries

The automated middle (orchestrator) is bookended by interactive human collaboration (shape-spec, walk-spec). Additional human touchpoints (handle-feedback, resolve-blockers) exist for handling edge cases. Automated commands never make architectural decisions or override human choices.
