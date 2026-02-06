# Workflow v2: Pitch Plan

## The Vision

A five-command spec lifecycle where the middle is fully automatable:

```
shape-spec (human + agent, interactive)
    ↓
 ┌──────────────────────────────────────────────────────────────┐
 │  orchestrator script (automated, model-agnostic)             │
 │                                                              │
 │  for each unchecked task:                                    │
 │      do-task  →  make check (gate)  →  audit-task            │
 │                                                              │
 │  make all (gate)                                             │
 │  run-demo  →  if issues: adds tasks, loops back              │
 │                                                              │
 │  audit-spec  →  if issues: adds tasks, loops back            │
 │               →  if pass: notify human                       │
 └──────────────────────────────────────────────────────────────┘
    ↓
walk-spec (human + agent, interactive)
```

Human touches: shaping (beginning) and walking (end). Everything in between runs unattended.

---

## Commands

### shape-spec (interactive)

**Suggested model:** Strong planner (e.g., Opus via TUI). Any model with good planning and communication works.

Plan the work with the user. Produce all spec artifacts and push.

**Responsibilities:**
- Resolve or create GitHub issue (gh issue view / gh issue create)
- Clarify scope, gather visuals, references, product context
- Propose and confirm standards
- Define non-negotiables with the user — things the auditors should never compromise on. Write these into spec.md under **Note to Code Auditors**.
- Write the acceptance criteria (spec.md) — the immutable contract
- Write the demo plan (demo.md) — narrative, accessible, concrete
- Write the task plan (plan.md) — checklist tasks, informed by the demo
- Write standards.md, references.md
- Create branch (gh issue develop) and check it out
- First commit: spec docs only
- Update GitHub issue body with Spec Summary section
- Push branch with -u
- Stop. Hand off to the orchestrator.

**Does NOT:**
- Start implementation
- Run verification
- Touch signposts.md, audit-log.md, or audit.md (those don't exist yet)

---

### do-task (automated)

**Suggested model:** Fast, capable implementer (e.g., Sonnet via headless CLI). Cost-efficiency matters — this runs many times.

Pick up the next unchecked task, implement it, verify it, commit it.

**Responsibilities:**
- Read spec.md — understand acceptance criteria and non-negotiables
- Read plan.md — find the first unchecked `[ ]` task
- Read signposts.md — learn from previous errors before starting (verify claims against the evidence before trusting them)
- Read standards.md — know what standards apply
- Read the task description and implement it
- Run the task gate (e.g., `make check`) to catch obvious issues early — if it fails, fix and retry before exiting. This avoids a full loop restart for trivial issues like formatting or type errors.
- If stuck on an issue:
  - Write a signpost to signposts.md with evidence (see Signpost Rules below)
  - Continue if possible, or exit as blocked
- Check off the task: `[ ]` → `[x]` in plan.md
- Commit with a descriptive message (scoped to this task)

**Does NOT:**
- Run the demo
- Audit its own work
- Create branches, push, or touch GitHub issues
- Modify spec.md (acceptance criteria, non-negotiables are immutable)
- Update roadmap.md

**Exit signal (machine-readable, written to stdout or a status file):**
- `do-task-status: complete` (task done, committed)
- `do-task-status: blocked` (stuck, signpost written with evidence)
- `do-task-status: all-done` (no unchecked tasks remain)

---

### audit-task (automated)

**Suggested model:** Different model from do-task for independence (e.g., Codex medium reasoning via headless CLI). Lightweight review — speed matters.

Audit the most recently completed task. Lightweight, focused, fast.

**Responsibilities:**
- Read spec.md — check against acceptance criteria and non-negotiables
- Read plan.md — identify the most recently checked-off task
- Read the task description
- Read the implementation (use git diff of the task's commit, or read cited files)
- Read standards.md — check standards adherence in the changed files only
- Evaluate:
  - Does the implementation match what the task description asked for?
  - Any non-negotiable violations?
  - Any standards violations in the changed files?
  - Any obvious quality issues (dead code, missing error handling, untested paths)?
- If issues found:
  - Uncheck the task: `[x]` → `[ ]` in plan.md
  - Append specific fix items as new `[ ]` entries below the task:
    ```
    - [ ] Task 6: Use OpenRouterModel for OpenRouter endpoints
      - [ ] Fix: Missing type annotation on routing_settings field (audit round 1)
    ```
  - Write relevant signposts to signposts.md (with evidence)
- If clean: confirm the task passes
- Append a brief entry to audit-log.md (task name, pass/fail, notes)

**Does NOT:**
- Score rubrics (that's audit-spec)
- Check completeness of the full spec (that's audit-spec)
- Run the demo or verification gates (orchestrator handles gates)
- Push, create PRs, or touch GitHub
- Modify spec.md

**Exit signal:**
- `audit-task-status: pass` (task is clean)
- `audit-task-status: fail` (task unchecked, fix items added)

---

### run-demo (automated)

**Suggested model:** Capable implementer with good debugging skills (e.g., Sonnet via headless CLI).

Execute the demo and, if it fails, investigate and route issues back to the task loop.

**Responsibilities:**
- Read demo.md — understand the demo steps and expected outcomes
- Read signposts.md — check for known issues that might affect the demo
- Execute each demo step and record the result
- If a step passes: record it in demo.md Results
- If a step fails:
  - Investigate the root cause (read code, logs, error output)
  - If tests pass but demo fails: identify the test gap — what tests are missing that would have caught this?
  - Write signpost with evidence of the failure
  - Add new `[ ]` items to plan.md (test gap items and/or fix items)
  - Record the failure in demo.md Results
- Append a summary entry to audit-log.md (demo run, pass/fail, notes)
- Commit demo.md changes

**Does NOT:**
- Fix code itself (it adds tasks for do-task to pick up)
- Modify spec.md
- Push or touch GitHub

**Exit signal:**
- `run-demo-status: pass` (all steps passed)
- `run-demo-status: fail` (issues found, tasks added to plan.md)

---

### audit-spec (automated)

**Suggested model:** Strong reasoner, different from do-task (e.g., Codex high reasoning via headless CLI). Deep review — quality matters more than speed.

Bird's-eye audit of the full implementation after all tasks and demo pass.

**Responsibilities:**
- Read everything: spec.md (acceptance criteria, non-negotiables), plan.md, standards.md, references.md, demo.md (including results), signposts.md, audit-log.md
- Read implementation files and tests referenced by the plan
- Read audit-log.md — check for regressions (tasks that failed, were fixed, then might have regressed)
- Score the 5-prong rubric: Performance, Intent, Completion, Security, Stability (1-5)
- Check non-negotiables — these must all pass. No exceptions, no caveats.
- Check standards adherence across the full implementation (not just per-task diffs)
- Check demo results — did the demo pass? Are the results convincing?
- Check completeness — all acceptance criteria met?
- Check cross-cutting concerns — consistency across files, architectural coherence, things that only emerge at the full-picture level
- Categorize action items:
  - Default routing: High/Medium → Fix Now, Low → Defer (configurable)
  - Fix Now items: append as new `[ ]` entries in plan.md
  - Deferred items: create GitHub issues with links back to current spec
- Write audit.md with:
  - Machine-readable status line: `status: pass` or `status: fail`
  - `fix_now_count: N`
  - Rubric scores
  - Non-negotiable compliance (explicit pass/fail per item)
  - Standards adherence with file:line citations
  - Demo status
  - Action items
- Append a summary entry to audit-log.md (round number, pass/fail, item count)
- Update Spec Progress comment on GitHub issue

**Does NOT:**
- Fix anything
- Run the demo itself (reads results from demo.md)
- Push or create PRs
- Touch roadmap.md
- Modify spec.md

**Exit signal (in audit.md):**
- `status: pass` → orchestrator proceeds to notify human
- `status: fail` → orchestrator loops back to do-task

---

### walk-spec (interactive)

**Suggested model:** Strong communicator (e.g., Opus via TUI). Needs excellent interactive skills for the demo walkthrough.

The human validation checkpoint. Demo the feature, submit the PR, evaluate learnings.

**Responsibilities:**
- Read all spec files (spec.md, plan.md, standards.md, demo.md, signposts.md, audit.md, audit-log.md)
- Read implementation files (follow file:line citations from audit)
- Run full verification gate — confirm it still passes
- Present implementation summary to user (key changes, acceptance criteria, audit scores, non-negotiable compliance)
- Surface any deferred items — confirm user accepts them
- Interactive demo walkthrough:
  - Set the stage (what the feature is, why it matters)
  - Execute each demo step with the user, showing results
  - Confirm each step before moving on
  - If a demo step fails: stop, investigate, discuss with user
- Prepare and submit PR (gh pr create)
- Mark spec as ✅ in roadmap.md
- Evaluate whether to suggest running `/discover-standards`:
  - Skim signposts.md and audit-log.md for patterns that might warrant new or revised standards
  - If anything stands out (e.g., a recurring issue, a non-obvious workaround that others would hit), recommend the user run `/discover-standards` as a follow-up and briefly explain why
- Commit final changes (roadmap update)
- Push the branch
- Update Spec Progress comment on GitHub with PR link
- Report: share PR URL, note follow-ups, note whether `/discover-standards` is suggested

**Does NOT:**
- Implement or fix code (if demo fails, discuss with user — don't silently fix)
- Run audit-spec
- Create branches (branch already exists from shape-spec)

---

## The Orchestrator Script

A deliberately simple script. The intelligence is in the agents, not the orchestrator. The orchestrator's only job is sequencing, gating, and routing.

**Inputs:**
- Spec folder path (or spec_id to resolve it)
- CLI + model configuration per command (defaults provided, all overridable)

**Verification gates — run by the orchestrator, not the agents:**

| Gate | Command | When | What it runs |
|------|---------|------|--------------|
| Task gate | `make check` (or equivalent) | After each do-task, before audit-task | Format, lint, typecheck, unit tests — fast, catches obvious breaks |
| Spec gate | `make all` | After all tasks pass, before run-demo | Full suite including coverage and quality tests |
| Demo gate | (run-demo exit signal) | After run-demo | Demo pass/fail |
| Audit gate | (audit.md status field) | After audit-spec | Spec audit pass/fail |

Agents also run verification internally (do-task runs `make check` before exiting) so they can self-fix trivial issues without a full loop restart. The orchestrator re-runs the same gate as a hard confirmation — if the agent claims it passed but the orchestrator's gate disagrees, the orchestrator bounces back to do-task with the error output as context. Belt and suspenders.

**Logic:**

```
Phase 1: Task Loop
    while plan.md has unchecked tasks:

        invoke do-task
            → implements next unchecked task, commits

        run task gate (make check)
            → if fails: re-invoke do-task with error output and
              guidance that the task gate must pass to proceed
            → if passes: continue

        invoke audit-task
            → if fail: task unchecked, fix items added → loop continues
            → if pass: move to next task

Phase 2: Spec Verification
    run spec gate (make all)
        → if fails: add failure context, loop back to Phase 1

Phase 3: Demo
    invoke run-demo
        → if fail: new tasks added to plan.md → loop back to Phase 1
        → if pass: continue

Phase 4: Spec Audit
    invoke audit-spec
        → if fail: new items in plan.md → loop back to Phase 1
        → if pass: notify human → ready for walk-spec

Progress Detection:
    After each full Phase 1 → 2 → 3 → 4 cycle, compare plan.md state
    to the previous cycle. If no net progress was made (same tasks
    unchecked, same items failing), stop and notify the human with
    full context: what's stuck, what's been tried (from signposts.md
    and audit-log.md), and what might need human judgment.

    This is not an arbitrary iteration limit. It's a staleness
    detector — the loop stops when it's spinning, not after N tries.
```

**The orchestrator does NOT:**
- Create branches, push, or touch GitHub (that's shape-spec and walk-spec)
- Make implementation decisions
- Choose which task to work on (plan.md checklist order decides)
- Run agents with hardcoded models (model selection is configurable)

---

## Spec Folder Structure

```
agent-os/specs/{YYYY-MM-DD-HHMM-spec_id-feature-slug}/
├── spec.md          # Acceptance criteria, non-negotiables, Note to Code Auditors (IMMUTABLE after shaping)
├── plan.md          # Checklist tasks, decision record, metadata (MUTABLE — the work tracker)
├── standards.md     # Applicable standards list
├── references.md    # Implementation files, issues, related specs
├── demo.md          # Demo plan (narrative) + demo results (appended per run)
├── signposts.md     # Errors, dead ends, quirks — with evidence (problems only)
├── audit.md         # Latest spec-level audit: rubric, standards, status
├── audit-log.md     # Running log of all audit-task, run-demo, and audit-spec results
└── visuals/         # Optional mockups, diagrams, screenshots
```

**Immutable vs. Mutable:**
- **spec.md** is written during shape-spec and not modified by any automated command. Acceptance criteria and non-negotiables are the contract. If an agent modifies spec.md, that's a red flag.
- **plan.md** is the living work tracker. Tasks get checked off, fix items get added, new tasks appear from audits. This is expected to change constantly.
- **demo.md** plan section is immutable (written during shape); results section is append-only.
- **signposts.md** and **audit-log.md** are append-only.

---

## File Formats

### spec.md — the immutable contract

```markdown
spec_id: s0.1.28
issue: https://github.com/OWNER/REPO/issues/NNN
version: v0.1

# Spec: OpenRouter Full Support

## Problem
[Brief statement of what's broken or missing — from shape discussion]

## Goals
- Tool-only execution path across all providers
- OpenRouter routing constrained to compatible endpoints
- Unified quality/production behavior

## Non-Goals
- Multi-provider fallback chains
- Custom model routing UI

## Acceptance Criteria
- [ ] Tool-only runtime path enforced with provider compatibility assertions
- [ ] OpenRouter requests propagate require_parameters=true by default
- [ ] OpenRouterModel used for all OpenRouter execution paths
- [ ] Quality harness and production exercise identical behavior
- [ ] All tests pass including quality suite
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No mixed output modes.** The runtime must use tool output exclusively. Any code path that falls back to prompted or native output is a failure, even if tests pass.
2. **OpenRouter routing must be typed.** All routing config must use Pydantic models with Field(..., description=...). No dict[str, Any] or untyped config.
3. **No test deletions or modifications to make audits pass.** If a test fails, the code must be fixed, not the test.
```

### plan.md — the mutable work tracker

```markdown
spec_id: s0.1.28
issue: https://github.com/OWNER/REPO/issues/NNN
version: v0.1

# Plan: OpenRouter Full Support

## Decision Record
[Why this work exists — brief rationale]

## Tasks
- [x] Task 1: Save Spec Documentation
- [x] Task 2: Collapse runtime to tool-only output
  - Refactor runtime.py so agent execution always uses tool output
  - Remove PromptedOutput execution path
  - Preserve required-tool gating
- [ ] Task 3: Simplify provider capability logic
  - Refactor providers.py: remove auto/prompted/native logic
  - Keep provider detection and tool-capability checks
  - Expose tool-only compatibility assertion
- [ ] Task 4: Add OpenRouter routing settings in config
  ...
```

**Conventions:**
- Tasks are top-level `- [ ]` items with descriptive titles
- Sub-bullets under each task describe what to do (not checkboxes — the task is atomic)
- audit-task appends fix items as indented `- [ ]` under the relevant task
- audit-spec appends new items at the bottom of the Tasks section
- Acceptance criteria live in spec.md, NOT here — plan.md is purely about work tracking

### demo.md — plan + results

```markdown
# Demo: OpenRouter Full Support

The project now works whether you use local models or OpenRouter.
In this demo, we'll prove how both work, how to switch between them,
and why this matters for reliability.

## Steps

1. Run the pipeline with the default local provider — expected: translation completes successfully
2. Edit config to set provider to OpenRouter with require_parameters = true
3. Run the same pipeline — expected: translation completes using OpenRouter routing
4. Check logs for provider_family: openrouter entries — expected: correct routing confirmed

## Results

### Run 1 — post-task-loop (2026-02-05 14:30)
- Step 1: PASS — translation completed, 47 lines processed
- Step 2: PASS — config updated
- Step 3: PASS — translation completed via OpenRouter
- Step 4: PASS — logs show provider_family: openrouter for all requests
- **Overall: PASS**
```

### signposts.md — problems with evidence

```markdown
# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.** A conclusion without proof
(e.g., "OpenRouter doesn't support tools") will mislead future iterations.
Include the exact error, command, or output that demonstrates the problem.

---

## OpenRouterModel import path
- **Task:** 6
- **Problem:** `from pydantic_ai.models.openrouter import OpenRouterModel` doesn't exist
- **Evidence:**
  ```
  $ python -c "from pydantic_ai.models.openrouter import OpenRouterModel"
  ModuleNotFoundError: No module named 'pydantic_ai.models.openrouter'
  ```
  Checked pydantic-ai 0.9.1 source — no openrouter submodule exists in models/.
- **Tried:** Various import paths from pydantic-ai docs
- **Solution:** Separate package: `pip install pydantic-ai-openrouter`, then `from pydantic_ai_openrouter import OpenRouterModel`
- **Files affected:** runtime.py, openai_runtime.py

## OpenRouter tool call format
- **Task:** 5
- **Problem:** OpenRouter returned 400 errors on tool call requests
- **Evidence:**
  ```
  HTTP 400: {"error": {"message": "Invalid tool_choice value", "code": 400}}
  ```
  Request payload had `tool_choice: {"type": "function", "name": "output"}` —
  OpenRouter expects `tool_choice: "auto"` or `tool_choice: "required"`, not
  the OpenAI object format.
- **Tried:** Passing OpenAI-format tool_choice (the error above)
- **Solution:** Use `tool_choice: "required"` for OpenRouter endpoints. Provider detection
  in providers.py now selects the correct format.
- **NOT the issue:** OpenRouter does support tools. The initial error was a format mismatch, not a capability gap.
- **Files affected:** providers.py, openai_runtime.py
```

### audit-log.md — running history

High-level summaries only. This file can get long over many loop cycles, so entries should be concise — just enough for a future auditor to spot regressions and patterns. Full details live in audit.md (for spec audits) and git history (for task audits).

```markdown
# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): PASS — clean, no issues
- **Task 3** (round 1): FAIL — missed private IP detection in providers.py
- **Task 3** (round 2): PASS — private IP fix applied, Task 2 still clean
- **Task 4** (round 1): PASS
- **Task 5** (round 1): PASS
- **Task 6** (round 1): PASS — used pydantic-ai-openrouter package (see signpost)
- **Demo** (run 1): FAIL — Step 3: OpenRouter 400 on tool_choice format (see signpost)
- **Task 12** (round 1): PASS — tool_choice format fix
- **Task 13** (round 1): PASS — added OpenRouter tool_choice test
- **Demo** (run 2): PASS — all 4 steps
- **Spec Audit** (round 1): PASS — 5/5 all rubrics, 3/3 non-negotiables, 0 fix-now
```

### audit.md — latest spec audit (with machine-readable header)

```markdown
status: pass
fix_now_count: 0

# Audit: s0.1.28 OpenRouter Full Support

- Spec: s0.1.28
- Issue: https://github.com/OWNER/REPO/issues/112
- Date: 2026-02-05
- Round: 1

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 5/5
- Completion: 5/5
- Security: 5/5
- Stability: 5/5

## Non-Negotiable Compliance
1. No mixed output modes: **PASS** — runtime.py has no output-mode branching (runtime.py:403)
2. OpenRouter routing typed: **PASS** — all routing config uses Pydantic models (config.py:155, config.py:166)
3. No test deletions: **PASS** — git log shows no test file deletions or assertion weakening

## Demo Status
- Latest run: PASS (Run 2, 2026-02-05 16:15)
- All 4 steps passed

## Standards Adherence
[file:line citations per standard]

## Regression Check
- Reviewed audit-log.md: no regressions detected
- Task 3 was fixed in round 2; fix verified and stable

## Action Items

### Fix Now
- None.

### Deferred
- None.
```

---

## Responsibility Matrix

Every discrete action in the lifecycle, assigned to exactly one owner.

| Action | Owner | Notes |
|--------|-------|-------|
| **GitHub & Branch Management** | | |
| Resolve/create GitHub issue | shape-spec | gh issue view / gh issue create |
| Create branch | shape-spec | gh issue develop |
| First commit (spec docs) | shape-spec | Spec docs only |
| Push branch | shape-spec | git push -u |
| Update GitHub issue body (Spec Summary) | shape-spec | Edit issue body, don't comment |
| Update Spec Progress comment (during loop) | audit-spec | GitHub issue comment |
| Create PR | walk-spec | gh pr create |
| Push final changes | walk-spec | git push |
| Update Spec Progress with PR link | walk-spec | GitHub issue comment |
| | | |
| **Spec Artifacts (written once during shape)** | | |
| Write spec.md (acceptance criteria, non-negotiables) | shape-spec | IMMUTABLE after this |
| Write demo.md (plan section) | shape-spec | Plan section immutable; results appended later |
| Write plan.md (tasks as checklists) | shape-spec | Mutable work tracker |
| Write standards.md, references.md | shape-spec | |
| | | |
| **Implementation** | | |
| Read next unchecked task | do-task | First `[ ]` in plan.md |
| Read signposts (verify evidence before trusting) | do-task | signposts.md |
| Implement a single task | do-task | Scoped to that task only |
| Check off task | do-task | `[ ]` → `[x]` in plan.md |
| Commit task work | do-task | Descriptive message per task |
| | | |
| **Verification Gates (run by orchestrator)** | | |
| Task gate (format, lint, typecheck, unit tests) | orchestrator | `make check` after each do-task |
| Spec gate (full test suite) | orchestrator | `make all` after all tasks complete |
| | | |
| **Task-Level Audit** | | |
| Audit most recent task | audit-task | Reads git diff + standards + non-negotiables |
| Uncheck task if issues found | audit-task | `[x]` → `[ ]` in plan.md |
| Add fix items under task | audit-task | Indented `[ ]` items in plan.md |
| Append to audit-log.md | audit-task | Task audit entry |
| | | |
| **Demo** | | |
| Execute demo steps | run-demo | Reads demo.md Steps |
| Write demo results | run-demo | Appends to demo.md Results |
| Investigate demo failures | run-demo | Root cause analysis, test gap detection |
| Add tasks for demo failures | run-demo | New `[ ]` items in plan.md |
| Append to audit-log.md | run-demo | Demo run entry |
| Commit demo.md changes | run-demo | |
| | | |
| **Spec-Level Audit** | | |
| Score rubric (5-prong) | audit-spec | Full implementation review |
| Check non-negotiables (explicit pass/fail) | audit-spec | From spec.md |
| Check acceptance criteria | audit-spec | From spec.md |
| Check standards (full codebase) | audit-spec | file:line citations |
| Check demo results | audit-spec | Reads demo.md Results |
| Check for regressions | audit-spec | Reads audit-log.md history |
| Write audit.md | audit-spec | With machine-readable status header |
| Append to audit-log.md | audit-spec | Spec audit entry |
| Categorize action items | audit-spec | Fix Now → plan.md, Defer → GitHub issues |
| Commit audit.md | audit-spec | |
| | | |
| **Signposts (append-only, with evidence)** | | |
| Write signpost for implementation issues | do-task | Must include evidence |
| Write signpost for audit findings | audit-task | Must include evidence |
| Write signpost for demo failures | run-demo | Must include evidence |
| | | |
| **Orchestration** | | |
| Manage do-task → gate → audit-task loop | orchestrator | Until all tasks checked |
| Run spec gate after task loop | orchestrator | make all |
| Invoke run-demo after spec gate | orchestrator | |
| Invoke audit-spec after demo passes | orchestrator | |
| Route audit-spec failures back to task loop | orchestrator | |
| Detect staleness (no progress between cycles) | orchestrator | Notify human with full context |
| Notify human when ready for walk-spec | orchestrator | |
| | | |
| **Walk & Close** | | |
| Run final verification gate | walk-spec | make all |
| Present implementation summary | walk-spec | Key changes, audit scores, non-negotiables |
| Interactive demo walkthrough with user | walk-spec | Step by step with confirmation |
| Mark spec ✅ in roadmap.md | walk-spec | |
| Suggest /discover-standards if warranted | walk-spec | Skim signposts + audit-log for patterns |
| Final commit | walk-spec | Roadmap update |

---

## Multi-Model Configuration

Models are suggestions, not requirements. The orchestrator accepts configuration for which CLI and model to use per command. Use whatever works for your setup.

| Command | Suggested Default | Why |
|---------|-------------------|-----|
| shape-spec | Strong planner (Opus) via TUI | Interactive, needs planning and communication |
| do-task | Fast implementer (Sonnet) via headless CLI | Cost-efficient for many iterations |
| audit-task | Different model from do-task (Codex medium) via headless CLI | Independence — don't grade your own homework |
| run-demo | Capable implementer (Sonnet) via headless CLI | Needs to execute commands and interpret results |
| audit-spec | Strong reasoner (Codex high) via headless CLI | Deep review, standards, architectural judgment |
| walk-spec | Strong communicator (Opus) via TUI | Interactive demo walkthrough |

Principles:
- **Auditors should differ from implementers** — avoids the "grading your own homework" problem
- **Implementers should be cost-efficient** — they run many times in the loop
- **Interactive commands need strong communication** — shape and walk are human-facing
- **Any headless CLI works** — claude -p, opencode -p, or whatever supports your models

---

## What Changes From v1

| Aspect | v1 (Current) | v2 (Proposed) |
|--------|--------------|---------------|
| Commands | shape, do, audit, fix, walk | shape, do-task, audit-task, run-demo, audit-spec, walk (fix absorbed into do-task) |
| Task granularity | do-spec does all tasks in one session | do-task does one task per invocation |
| Verification | make all once at the end | Task gate (make check) per task, spec gate (make all) after loop |
| Verification ownership | Agent runs make all | Agent runs gate internally (self-fix), orchestrator re-runs as hard confirmation |
| Commits | One big commit | One commit per task |
| Audit granularity | Full spec only | Per-task (audit-task) + full spec (audit-spec) |
| Demo | Section in plan.md, no separate validation | Separate demo.md, run-demo command with failure investigation |
| Contract vs. work | Everything in plan.md | spec.md (immutable contract) + plan.md (mutable tasks) |
| Non-negotiables | Not explicit | Written in spec.md, checked by every auditor |
| Error memory | None | signposts.md with mandatory evidence |
| Audit history | None | audit-log.md (running record) |
| Regression detection | None | audit-spec reads audit-log.md for regressions |
| Task tracking | Markdown sections | `[ ]`/`[x]` checklists |
| Automation | Manual command-by-command | Orchestrator script with verification gates |
| Loop termination | N/A (manual) | Staleness detection (no progress between cycles) |
| Model diversity | Same model for everything | Different models per role (configurable) |
| Roadmap update | Not part of workflow | walk-spec marks ✅ |
| Standards evolution | Not part of workflow | walk-spec suggests /discover-standards when signposts or audit-log warrant it |

---

## Design Principles

1. **State lives in files, not in context.** Every command reads its inputs from the spec folder. Context rotation (session restarts) are safe because the filesystem is the source of truth.

2. **Immutable contract, mutable work.** spec.md is the contract — acceptance criteria and non-negotiables don't change during implementation. plan.md is the work tracker — tasks get checked, unchecked, and added freely. Separating these prevents agents from weakening the spec to make their job easier.

3. **Evidence over conclusions.** Signposts must include proof. An agent saying "X doesn't work" without evidence is worse than no signpost at all, because it misleads every future iteration.

4. **The orchestrator is dumb.** It sequences commands, runs verification gates, and detects staleness. All intelligence lives in the agents. This keeps the automation simple, debuggable, and tool-agnostic.

5. **Verification is belt and suspenders.** Agents run verification internally (so they can self-fix trivial issues without a full loop restart), and the orchestrator re-runs the same gate externally as a hard confirmation. The agent's self-check is a convenience; the orchestrator's gate is the authority.

6. **Different eyes for different jobs.** Implementers and auditors should be different models. This isn't a hard rule, but it avoids the bias of self-review.

7. **Standards are the long-term memory.** Signposts and audit logs are per-spec. Standards are permanent. walk-spec evaluates whether per-spec learnings should graduate to permanent standards.

8. **Good specs prevent infinite loops.** Rather than arbitrary circuit breakers, the workflow relies on quality upstream: clear acceptance criteria, concrete non-negotiables, demo-first test planning, and evidence-based signposts. The orchestrator's staleness detector is a safety net, not a design constraint.
