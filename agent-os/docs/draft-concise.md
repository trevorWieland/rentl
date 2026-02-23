# Agent OS Workflow Guide

A spec-driven development workflow powered by AI agents and an automated orchestrator. Works with any tech stack.

---

## TL;DR

1. **Shape** (`/shape-spec`, interactive) -- define what to build with spec.md, plan.md, demo.md
2. **Build** (`orchestrate.sh`, automated) -- agents implement, verify, audit, demo, and audit again in a loop
3. **Ship** (`/walk-spec`, interactive) -- validate the demo and submit the PR

The orchestrator handles everything between shaping and shipping. If it stalls, use `/resolve-blockers`. After PR review, use `/handle-feedback`.

---

## Command Cheat Sheet

| Command | Mode | Model | What it does | Exit signals |
|---------|------|-------|-------------|--------------|
| `/shape-spec` | Interactive | Opus | Plan work, produce spec artifacts, push branch | (none -- ends with handoff) |
| `/do-task` | Headless | Sonnet | Implement one task, run gate, commit | `complete` / `all-done` / `blocked` / `error` |
| `/audit-task` | Headless | Codex | Audit last task, uncheck + add fixes if issues | `pass` / `fail` / `error` |
| `/run-demo` | Headless | Sonnet | Execute demo plan, add fix tasks if failures | `pass` / `fail` / `error` |
| `/audit-spec` | Headless | Codex | Full audit: rubrics, non-negotiables, regressions | `status: pass\|fail` in audit.md |
| `/walk-spec` | Interactive | Opus | Interactive demo walkthrough, submit PR | (none -- ends with PR URL) |
| `/handle-feedback` | Interactive | Opus | Triage PR comments, route to tasks | `resolved` / `tasks-added` / `no-feedback` / `error` |
| `/resolve-blockers` | Interactive | Opus | Diagnose orchestrator halts, reconcile artifacts | `resolved` / `deferred` / `partial` / `no-blockers` / `error` |

**Supporting commands:** `/plan-product` (product docs), `/inject-standards` (load standards), `/discover-standards` (extract standards), `/index-standards` (rebuild index), `/sync-roadmap` (sync with GitHub).

**Deprecated:** `/do-spec` and `/fix-spec` redirect to `/do-task`.

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

**Post-PR flow:**

```
PR created --> reviewers comment --> handle-feedback --> [if tasks: orchestrator --> walk-spec] --> merge

orchestrator halts --> resolve-blockers --> re-run orchestrator
```

---

## Common Workflows

### Start a new feature

```bash
# 1. Shape the spec (interactive, in Claude Code TUI plan mode)
/shape-spec

# 2. Run the orchestrator (automated)
./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-05-2240-s0.1.35-cli-exit-codes

# 3. Walk and submit (interactive, in Claude Code TUI)
/walk-spec
```

### Resume after orchestrator halt

```bash
# 1. Investigate the halt (interactive)
/resolve-blockers

# 2. Re-run the orchestrator
./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-05-2240-s0.1.35-cli-exit-codes
```

### Handle PR feedback

```bash
# 1. Triage review comments (interactive)
/handle-feedback

# 2. If fix tasks were added, re-run orchestrator then walk-spec
./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-05-2240-s0.1.35-cli-exit-codes
/walk-spec
```

### Set up Agent OS in a new project

1. Copy `.claude/commands/agent-os/` and `agent-os/scripts/` into your repo
2. Configure verification gates (see [Verification Gates](#verification-gates))
3. Optional: run `/plan-product` for product docs
4. Optional: run `/discover-standards` for coding standards
5. Run `/shape-spec` to create your first spec

---

## Getting Started

Copy these directories into your repository:

- `.claude/commands/agent-os/` -- agent command definitions
- `agent-os/scripts/` -- orchestrator script

Then configure your verification gates. The orchestrator expects two shell commands:

| Gate | Default | Purpose | When |
|------|---------|---------|------|
| Task gate | `make check` | Fast checks (format, lint, type, unit) | After each task |
| Spec gate | `make all` | Full checks (+ integration, quality) | After all tasks, before demo |

Set via `ORCH_TASK_GATE` and `ORCH_SPEC_GATE`. Any command returning exit 0 on success works. Examples:

```bash
# Node.js
ORCH_TASK_GATE="npm run lint && npm test" ORCH_SPEC_GATE="npm run test:all"

# Rust
ORCH_TASK_GATE="cargo clippy && cargo test" ORCH_SPEC_GATE="cargo test --all-features"

# Go
ORCH_TASK_GATE="go vet ./... && go test ./..." ORCH_SPEC_GATE="go test -race -count=1 ./..."
```

---

## Prerequisites

**Required by Agent OS:**

| Tool | Version | Purpose |
|------|---------|---------|
| [gh](https://cli.github.com/) | latest | GitHub CLI |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | latest | Agent CLI (`claude -p` for headless) |
| make | any | Default gates (replaceable) |
| bash | >= 4.0 | Orchestrator script |

Your project adds its own runtime, package manager, linter, and test runner.

---

## Spec Folder Structure

Each spec lives in `agent-os/specs/{YYYY-MM-DD-HHMM-spec_id-feature-slug}/`.

| File | Mutability | Purpose |
|------|------------|---------|
| `spec.md` | **Immutable** | Acceptance criteria, non-negotiables. The contract. |
| `plan.md` | Mutable | Task checklist, fix items from audits. The work tracker. |
| `demo.md` | Plan: immutable, Results: append-only | Demo steps + recorded results per run. |
| `standards.md` | Static | Applicable standards for this spec. |
| `references.md` | Static | Implementation files, issues, related specs. |
| `signposts.md` | Append-only (Status updatable) | Problems with mandatory evidence. |
| `audit-log.md` | Append-only | History of audits, demos, spec audits. |
| `audit.md` | Overwritten per audit | Latest audit with machine-readable `status:` header. |
| `visuals/` | Static | Optional mockups, diagrams, screenshots. |

**Key invariant:** `spec.md` is never modified by automated commands. The orchestrator reverts + amends if an agent touches it. Only `resolve-blockers` can modify spec.md, with explicit user approval after showing the exact diff.

---

## Key Directories

| Path | Purpose |
|------|---------|
| `.claude/commands/agent-os/` | Agent command definitions (markdown files) |
| `agent-os/scripts/` | Orchestrator and supporting scripts |
| `agent-os/standards/` | Project coding standards (you create these) |
| `agent-os/product/` | Product docs: mission, roadmap, tech stack |
| `agent-os/specs/` | Spec folders (one per feature) |

---

## Core Commands

### shape-spec

> Plan the work with the user. Produce all spec artifacts and push.

- **Mode:** Interactive (TUI) -- suggested model: Opus
- **Input:** Issue number/URL, or pick from candidates
- **Output:** Spec folder with spec.md, plan.md, demo.md, standards.md, references.md, optional visuals/. Branch created and pushed.

<details>
<summary>Full process (13 steps)</summary>

Steps 1-11 are discussion only -- no branches, files, or git until Step 12.

1. **Resolve the Spec Issue.** Three paths: user provides issue, create new issue (determine next `spec_id` from GitHub), or pick next from roadmap (via optional `list-candidates.py` script).
2. **Clarify Scope.** Use issue title/body. Ask only if unclear.
3. **Gather Visuals.** Mockups, screenshots, or "none".
4. **Reference Implementations.** Similar code paths.
5. **Product Context.** Skim `agent-os/product/` if it exists.
6. **Standards.** Read `agent-os/standards/index.yml`, propose relevant standards.
7. **Non-Negotiables.** Must be specific, verifiable, and important.
8. **Acceptance Criteria.** Observable, scoped, complete.
9. **Demo Plan.** Narrative format: what, why, then concrete steps with expected outcomes.
10. **Task Plan.** Checklist. Task 1 = "Save Spec Documentation". No task for gates.
11. **Spec Folder Name.** `YYYY-MM-DD-HHMM-{spec_id}-{feature-slug}/`.
12. **Create Branch, Save, Commit, Push.** Branch via `gh issue develop`. Write files. Check off Task 1. Commit. Update issue body. Push.
13. **Stop.** Do not start implementation.

</details>

**Exit:** No machine-readable signal. Ends with handoff instructions.

---

### do-task

> Pick up the next unchecked task, implement it, verify, commit. One task per invocation.

- **Mode:** Headless -- suggested model: Sonnet (cost-efficiency matters)
- **Input:** Spec folder path (from orchestrator)
- **Output:** Implemented task, updated plan.md checkbox, commit

<details>
<summary>Full process</summary>

1. **Resolve Spec.** Read plan.md metadata. Exit `error` if ambiguous.
2. **Load Context.** spec.md, plan.md (first unchecked task), standards.md, signposts.md (verify evidence before trusting claims).
3. **Identify Task.** First unchecked `[ ]` task. If fix items are indented beneath it, address those too. If none remain: exit `all-done`.
4. **Implement.** Follow steps, adhere to standards, respect non-negotiables, keep changes scoped.
5. **Run Task Gate.** Fix failures and re-run. If stuck, write signpost and exit `blocked`.
6. **Check Off Task.** `[ ]` to `[x]` in plan.md. Check off fix items too.
7. **Signpost.** Write to signposts.md if non-obvious issues encountered.
8. **Commit.** `git commit -m "Task N: [description]"`.

</details>

**Exit signals:** `complete` | `blocked` | `all-done` | `error`

**Does NOT:** Run demo, audit own work, create branches, push, touch GitHub issues, modify spec.md, update roadmap, ask user questions.

---

### audit-task

> Audit the most recently completed task. Lightweight and focused.

- **Mode:** Headless -- suggested model: different provider from do-task
- **Input:** Spec folder path (from orchestrator)
- **Output:** Updated plan.md (pass or uncheck + fix items), audit-log.md entry, commit

<details>
<summary>Full process</summary>

1. **Resolve Spec.** Same as do-task.
2. **Identify Task.** Most recently checked-off top-level `[x]` task.
3. **Load Context.** spec.md, plan.md, standards.md, signposts.md (check Status field), `git diff HEAD~1`.
4. **Evaluate against:**
   - Task fidelity -- does implementation match description?
   - Non-negotiable compliance -- hard failures
   - Standards adherence -- cite rules and file:line
   - Quality -- dead code, missing error handling, naming, security
5. **Cross-Reference Signposts.** (See [Cross-Reference Protocol](#cross-reference-protocol))
6. **Verdict:** Pass (clean) or Fail (uncheck task, add `[ ] Fix:` items with file:line and round number).
7. **Signpost.** Write if non-obvious issues revealed.
8. **Update Audit Log.** `- **Task N** (round R): PASS|FAIL -- [summary]`
9. **Commit.** `git commit -m "Audit: Task N -- PASS|FAIL"`

</details>

**Exit signals:** `pass` | `fail` | `error`

**Does NOT:** Score rubrics, check overall completeness, run demo or gates, fix code, push, create PRs, modify spec.md.

---

### run-demo

> Execute the demo plan. If failures, investigate and add fix tasks.

- **Mode:** Headless -- suggested model: Sonnet
- **Input:** Spec folder path (from orchestrator)
- **Output:** Updated demo.md (results), plan.md (new tasks if failures), signposts.md, audit-log.md, commit

<details>
<summary>Full process</summary>

1. **Resolve Spec.**
2. **Load Context.** demo.md (steps + expected outcomes), spec.md, signposts.md.
3. **Execute Demo.** Run each step, compare against expected outcome. On fail: stop and investigate.
4. **Investigate Failures.** Read errors, check test coverage gaps, trace root cause. Write signpost (`Status: unresolved`). Add tasks to plan.md (tests first, then fix).
5. **Record Results.** Append to demo.md `## Results` section.
6. **Update Audit Log.** `- **Demo** (run N): PASS|FAIL -- [summary]`
7. **Commit.**

</details>

**Exit signals:** `pass` | `fail` | `error`

**Does NOT:** Fix code, modify spec.md, push, score rubrics.

---

### audit-spec

> Bird's-eye audit of the full implementation. Score rubrics, check non-negotiables, detect regressions.

- **Mode:** Headless -- suggested model: strong reasoner, different from do-task
- **Input:** Spec folder path (from orchestrator)
- **Output:** audit.md (machine-readable status), plan.md (Fix Now items), audit-log.md, GitHub issue comment, commit

<details>
<summary>Full process</summary>

1. **Resolve Spec.**
2. **Load Context.** All spec files + implementation + tests.
3. **Seven audit dimensions:**
   - **3a: Rubric Scores (1-5)** -- Performance, Intent, Completion, Security, Stability
   - **3b: Non-Negotiable Compliance** -- PASS/FAIL per item with file:line evidence
   - **3c: Standards Adherence** -- violations with rule, file:line, severity
   - **3d: Demo Status** -- did it pass? Results convincing?
   - **3e: Signpost Cross-Reference** -- (see [Cross-Reference Protocol](#cross-reference-protocol))
   - **3f: Regression Check** -- patterns in audit-log.md
   - **3g: Cross-Cutting Concerns** -- consistency, architecture, test gaps
4. **Categorize:** High/Medium -> Fix Now (plan.md). Low -> Defer (create GitHub issue).
5. **Write audit.md.** Machine-readable header: `status: pass|fail`, `fix_now_count: N`.
6. **Update Audit Log.**
7. **Report to GitHub.** Update "Spec Progress" comment on issue.
8. **Commit.**

</details>

**Pass criteria:** All rubric scores 5/5, all non-negotiables PASS, demo PASS, zero Fix Now items.

**Does NOT:** Fix anything, run demo, push, create PRs, touch roadmap, modify spec.md.

---

### walk-spec

> Human validation checkpoint. Interactive demo walkthrough, submit PR, update roadmap.

- **Mode:** Interactive (TUI) -- suggested model: Opus
- **Input:** Issue number/URL or spec_id
- **Output:** PR created, roadmap updated, branch pushed
- **Prerequisites:** All tasks checked, audit passes, demo passed, clean tree

<details>
<summary>Full process</summary>

1. **Resolve Spec.**
2. **Gather Context.** Read all spec + implementation files autonomously.
3. **Run Spec Gate.** Stop and report if it fails.
4. **Implementation Summary.** Key changes, acceptance criteria evidence, non-negotiable compliance, audit scores, demo status, deferred items.
5. **Interactive Demo Walkthrough.** For each step: explain, execute, show result, explain what it proves, confirm. On failure: stop, investigate, discuss options.
6. **Prepare PR.** Title: `{spec_id} {short title}`. Body: Summary, Spec section, Deferred section.
7. **Update Roadmap.** Mark complete if entry exists.
8. **Evaluate Standards Evolution.** Recommend `/discover-standards` if warranted.
9. **Push and Report.** Push branch, update issue comment, report PR URL.

</details>

**Does NOT:** Implement or fix code, run audit-spec, create branches, make decisions without user.

---

## Feedback and Blocker Commands

### handle-feedback

> Triage PR review comments, evaluate correctness, route valid feedback to tasks.

- **Mode:** Interactive (TUI) -- suggested model: Opus
- **When:** After PR creation when review comments arrive
- **Prerequisites:** Spec folder, existing PR, comments to process

<details>
<summary>Full process</summary>

1. **Resolve Spec and PR.** Find via `gh pr list --head 130-s0143-feature-name`.
2. **Fetch Feedback.** Four sources: inline review comments, review bodies, issue-style comments, check run annotations. Parse each into: ID, Source, File:line, Body, Is bot.
3. **Load Context.** spec.md, plan.md, signposts.md, standards.md, audit.md.
4. **Triage Each Item.** Read relevant code, evaluate correctness, check signposts, classify: `valid-actionable` | `valid-addressed` | `invalid` | `style-preference` | `out-of-scope` | `duplicate`.
5. **Present to User.** Grouped by classification. User can override.
6. **Execute Actions:**
   - valid-actionable: add Fix items, write signpost, uncheck task
   - valid-addressed: reply with file:line evidence
   - invalid: polite reply with evidence
   - style-preference: acknowledge; adopt if user wants
   - out-of-scope: create GitHub issue, reply with reference
7. **Update Audit Log.**
8. **Commit and Push.**

</details>

**Exit signals:** `resolved` | `tasks-added` | `no-feedback` | `error`

**Does NOT:** Fix code, merge PR, modify spec.md, run gates, make triage decisions autonomously, post without user approval.

---

### resolve-blockers

> Investigate orchestrator halts, propose solutions, reconcile artifacts.

- **Mode:** Interactive (TUI) -- suggested model: Opus
- **When:** Orchestrator halts (blocked, stuck task, stale cycles, audit contradictions)

<details>
<summary>Full process</summary>

1. **Resolve Spec.**
2. **Investigate.** Scan for: unresolved signposts, contradictory fix items, stuck tasks, architectural constraints, spec/reality mismatches. Verify by reading code at cited file:line.
3. **Present Blocker Report.** Per blocker: source, root cause, what's been tried. 2-3 options:
   - Option A (recommended): what, why, changes, risk
   - Option B: alternative
   - Option C: defer to future spec
4. **Reconcile Artifacts.** Per user decisions:
   - signposts.md: set Status to resolved/deferred, add Resolution
   - plan.md: remove contradictory fixes, add new ones, re-scope
   - spec.md: ONLY with explicit approval after showing exact diff
   - Deferred: create GitHub issue, update signpost, record URL
5. **Verify Consistency.** No contradictions between artifacts.
6. **Run Gate** if code changes made.
7. **Commit.**
8. **Advise Next Steps.**

</details>

**Exit signals:** `resolved` | `deferred` | `partial` | `no-blockers` | `error`

**Does NOT:** Implement code, run demo, audit implementation, push/create PRs, decide autonomously.

---

## Supporting Commands

| Command | Purpose | Key output |
|---------|---------|------------|
| `/plan-product` | Product docs (mission, roadmap, tech stack) | `agent-os/product/{mission,roadmap,tech-stack}.md` |
| `/inject-standards` | Load relevant standards into context | Standards content or `@` references |
| `/discover-standards` | Extract tribal knowledge into standards | `agent-os/standards/ux/progress-is-product.md` |
| `/index-standards` | Rebuild `agent-os/standards/index.yml` | Updated index file |
| `/sync-roadmap` | Sync `roadmap.md` with GitHub issues (`type:spec`) | Aligned roadmap + issues |

<details>
<summary>Supporting command details</summary>

### plan-product

Creates `agent-os/product/mission.md`, `roadmap.md`, `tech-stack.md` through interactive conversation. These give shape-spec context about your product. Typically run once when adopting Agent OS.

### inject-standards

Two modes:
- **Auto-suggest** (`/inject-standards`): analyzes context, suggests 2-5 relevant standards
- **Explicit** (`/inject-standards api` or `/inject-standards api/response-format`): injects specified standards

Three scenarios: conversation (full content), skill creation (`@` refs or full), shaping/planning (`@` refs or full). Called internally by shape-spec.

Path resolution: folder name -> all `.md` in that folder. `folder/file` -> specific file. `root` -> files directly in `agent-os/standards/`. `root/name` -> specific root file.

### discover-standards

Interactive process: identify 3-5 focus areas -> user picks one -> analyze 5-10 files -> present patterns -> user selects -> for each: ask "why", draft, confirm, create file -> update index -> offer another area.

Writing guidelines: lead with the rule, code examples, one standard per concept, bullets over paragraphs.

### index-standards

Scans all `.md` in `agent-os/standards/` and subfolders. Identifies new/deleted files. For new files: propose description, confirm with user. Write updated index (alphabetized, no `.md` extensions). Run after manually editing standards, or if suggestions seem stale. `/discover-standards` runs this automatically.

### sync-roadmap

Loads roadmap.md and GitHub issues (`type:spec`). Classifies each spec_id: match, roadmap-only, GitHub-only, conflict. Roadmap-only: create issue. GitHub-only: add entry. Conflicts: ask user (default: GitHub wins). Aligns dependencies. GitHub is source of truth for spec IDs.

</details>

---

## The Orchestrator

`agent-os/scripts/orchestrate.sh` -- sequences agents, runs gates, detects staleness, routes signals. The intelligence lives in the agents; the orchestrator only does sequencing, gating, and routing.

### Usage

```bash
./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-05-2240-s0.1.35-cli-exit-codes
./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-05-2240-s0.1.35-cli-exit-codes --config orchestrate.conf
```

Requires `spec.md` and `plan.md` in the spec folder.

### Cycle Phases

Each cycle runs four phases in order:

| Phase | What happens | On failure |
|-------|-------------|------------|
| 1. Task Loop | do-task -> task gate -> audit-task (per unchecked task) | Gate retries up to 3x; stuck tasks abort |
| 2. Spec Gate | Run full verification | Invoke do-task to fix, restart cycle |
| 3. Demo | run-demo | New tasks added, restart cycle |
| 4. Spec Audit | audit-spec, read `status:` from audit.md | Fail: restart cycle. Pass: exit successfully |

### Stop Conditions

The orchestrator stops when:

| Condition | Behavior |
|-----------|----------|
| Spec audit passes | Exit 0 (success) |
| Staleness detected | Abort: plan.md unchanged for `ORCH_STALE_LIMIT` cycles |
| Task stuck | Abort: same task retried `ORCH_MAX_TASK_RETRIES` times |
| Safety limit | Abort: `ORCH_MAX_CYCLES` reached |
| Agent blocked/error | Abort: see signposts.md |

### Signal Extraction

Two-tier extraction for agent exit signals:

1. **Primary:** Read from `$SPEC_FOLDER/.agent-status` file (deterministic)
2. **Fallback:** Grep agent stdout (fragile, backwards-compatible)

Status file is cleared before each invocation.

<details>
<summary>Exit signal handling tables</summary>

**do-task signals:**

| Signal | Action |
|--------|--------|
| `complete` | Continue to gate |
| `all-done` | Break task loop |
| `blocked` | Abort: "Human intervention needed. See signposts.md." |
| `error` | Abort, print last 20 lines |
| (empty) | Warn, continue (gate will verify) |
| (other) | Warn, continue |

**audit-task signals:**

| Signal | Action |
|--------|--------|
| `pass` | Continue; self-heal checkbox if needed |
| `fail` | Continue (fix items added, loop picks up unchecked task) |
| `error` | Abort, print last 20 lines |
| (empty) | Warn, continue |
| (other) | Warn, continue |

**run-demo signals:**

| Signal | Action |
|--------|--------|
| `pass` | Proceed to spec audit |
| `fail` | Restart cycle (new tasks added) |
| `error` | Abort, print last 20 lines |
| (empty) | Abort, print last 20 lines |
| (other) | Warn, continue |

**audit-spec:** Uses `status:` field from audit.md first line.

| Status | Action |
|--------|--------|
| `pass` | Exit successfully |
| `fail` | Restart cycle (Fix Now items added) |
| (other/missing) | Abort |

</details>

### Safety Mechanisms

| Mechanism | How it works |
|-----------|-------------|
| **Spec immutability guard** | MD5 snapshot at start. After each agent: compare, revert if changed, amend commit. |
| **Staleness detection** | MD5 plan.md per cycle. Unchanged for `ORCH_STALE_LIMIT` cycles -> abort. Only active after tasks exist. |
| **Task retry limit** | Same task label appearing consecutively increments counter. After `ORCH_MAX_TASK_RETRIES` -> abort. |
| **Gate retry** | Task gate failure -> re-invoke do-task with error output. Up to `MAX_GATE_RETRIES` (3) attempts. |
| **Checkbox self-heal** | After audit pass, verify checkbox persisted. If not, check it off + orphaned fix items, amend/commit. |
| **Concurrency lock** | `flock` on fd 9 prevents two instances on same spec folder. |
| **Agent timeout** | `ORCH_AGENT_TIMEOUT` seconds per invocation (default 1800). |
| **Cleanup trap** | EXIT/INT/TERM: kill timer, kill agent (TERM -> KILL after 5s), remove temp files, clear spinner. |

### Progress Display

- Spinner with phase name, model, elapsed time
- Green checkmark / red X per phase
- Cycle headers with remaining task count
- Warning indicators for retries, staleness, missing signals
- Victory fanfare on success (best-effort, platform-adaptive audio)

---

## Verification Gates

Two tiers, fully configurable:

| Gate | Default | What it runs | When |
|------|---------|-------------|------|
| Task gate | `make check` | Fast: format, lint, type, unit | After each task |
| Spec gate | `make all` | Full: + integration, quality | After all tasks, before demo |

Configure via `ORCH_TASK_GATE` / `ORCH_SPEC_GATE`. Any shell command returning 0 on success works.

**Belt-and-suspenders:** The agent runs the gate internally, then the orchestrator re-runs it as a hard external gate.

| Tech Stack | Task Gate | Spec Gate |
|------------|-----------|-----------|
| Python + make | `make check` | `make all` |
| Node.js | `npm run lint && npm test` | `npm run test:all` |
| Rust | `cargo clippy && cargo test` | `cargo test --all-features` |
| Go | `go vet ./... && go test ./...` | `go test -race -count=1 ./...` |
| Ruby | `bundle exec rubocop && bundle exec rspec --tag ~slow` | `bundle exec rspec` |
| Java/Maven | `mvn checkstyle:check test` | `mvn verify` |
| Multi-language | `./scripts/check.sh` | `./scripts/check-all.sh` |

---

## The Signpost System

> Institutional memory for a spec. Captures problems, solutions, and constraints with mandatory evidence.

**Purpose:** Prevent repeated failures, communicate constraints between agents, provide evidence for decisions, help resolve-blockers diagnose stuck loops.

**Rules:**
1. Every signpost must include evidence (exact error, command, output)
2. Status is machine-readable: `unresolved` | `resolved` | `deferred`
3. Append-only (new entries), but Status field can be updated
4. Only write for non-obvious issues that help future tasks/iterations

### Signpost usage by command

| Command | Reads | Writes | Updates Status |
|---------|-------|--------|----------------|
| do-task | Yes (verify evidence) | Yes (if non-obvious) | No |
| audit-task | Yes (cross-ref before fixes) | Yes (if non-obvious) | No |
| run-demo | Yes (known issues) | Yes (always for failures) | No |
| audit-spec | Yes (cross-ref before Fix Now) | No | No |
| resolve-blockers | Yes (investigate) | Yes | Yes |
| handle-feedback | Yes (check resolutions) | Yes (if non-obvious) | No |

### Cross-Reference Protocol

Before adding fix items, auditors must:

1. **Resolved signposts:** verify resolution in code. If working, do NOT re-open. If broken, add fix with NEW evidence.
2. **Architectural constraints:** do NOT require infeasible approaches. Propose alternatives or defer.
3. **Deferred signposts:** skip unless new blocking evidence.
4. **Unresolved signposts:** fair game for fix items.

---

## The Audit System

Two levels serving different purposes:

| Aspect | audit-task | audit-spec |
|--------|-----------|------------|
| **Scope** | Most recent task only | Full implementation |
| **Focus** | Fidelity, non-negotiables, standards, quality | Rubrics, non-negotiables, standards, demo, regressions |
| **Does NOT check** | Overall completeness, demo, other tasks' code | (checks everything) |
| **Output** | PASS/FAIL + fix items, audit-log entry | audit.md + Fix Now items + GitHub issues + audit-log |
| **Frequency** | After every task | After all tasks + demo pass |

### Rubric Dimensions (spec audit)

| Dimension | What it checks |
|-----------|---------------|
| Performance | No unnecessary computation, I/O, memory |
| Intent | Matches spec goals, solves right problem |
| Completion | All acceptance criteria met |
| Security | No injection, credentials, OWASP concerns |
| Stability | Error handling, no silent failures, edge cases |

**Pass criteria:** All scores 5/5 + all non-negotiables PASS + demo PASS + zero Fix Now items.

### Model Independence

Implementation and auditing use different AI models/providers -- avoid grading your own homework. Configure via `ORCH_*_MODEL` and `ORCH_*_CLI` variables.

---

## GitHub Integration

### Spec IDs

- Format: `sX.Y.ZZ` (e.g., `s0.1.05`)
- GitHub is source of truth
- Labels: `type:spec`, `status:planned`, `version:vX.Y`
- Sync with `/sync-roadmap`

### Branching and PRs

- `shape-spec` creates branch via `gh issue develop`
- One commit per task on the branch
- `walk-spec` submits PR. Body format: Summary, Spec (issue/audit/non-negotiables/demo), Deferred
- `handle-feedback` pushes feedback commits

---

## Configuration Reference

### Environment Variables

**CLI and model:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCH_CLI` | `claude -p --dangerously-skip-permissions` | Fallback CLI for implementation |
| `ORCH_DO_CLI` | `$ORCH_CLI` | CLI for do-task |
| `ORCH_AUDIT_CLI` | `codex exec --yolo` | CLI for audit-task |
| `ORCH_DEMO_CLI` | `$ORCH_CLI` | CLI for run-demo |
| `ORCH_SPEC_CLI` | `codex exec --yolo` | CLI for audit-spec |
| `ORCH_DO_MODEL` | `sonnet` | Model for do-task |
| `ORCH_AUDIT_MODEL` | `gpt-5.3-codex` | Model for audit-task |
| `ORCH_DEMO_MODEL` | `sonnet` | Model for run-demo |
| `ORCH_SPEC_MODEL` | `gpt-5.3-codex` | Model for audit-spec |

> Model names and CLI tools in defaults will evolve. The key principle: use different providers for implementation vs. auditing.

**Gates and limits:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCH_TASK_GATE` | `make check` | Task-level verification |
| `ORCH_SPEC_GATE` | `make all` | Spec-level verification |
| `ORCH_MAX_CYCLES` | `10` | Safety limit on cycles |
| `ORCH_COMMANDS_DIR` | `.claude/commands/agent-os` | Command file path |
| `ORCH_AGENT_TIMEOUT` | `1800` | Per-agent timeout (seconds) |
| `ORCH_MAX_TASK_RETRIES` | `5` | Max attempts per task |
| `ORCH_STALE_LIMIT` | `3` | Stale cycles before abort |

**Hardcoded:** `MAX_GATE_RETRIES` = 3 (gate retry attempts per task).

### Config File

```bash
./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-05-2240-s0.1.35-cli-exit-codes --config my-config.conf
```

Sourced as bash. Example:

```bash
# orchestrate.conf -- Node.js project
ORCH_TASK_GATE="npm run lint && npm test"
ORCH_SPEC_GATE="npm run test:all"
ORCH_DO_MODEL="sonnet"
ORCH_AUDIT_MODEL="o3"
ORCH_AGENT_TIMEOUT=2400
```

---

## Design Principles

| Principle | Description |
|-----------|-------------|
| **Immutable contract** | spec.md never changes after shaping. plan.md is the mutable tracker. Only resolve-blockers can touch spec.md, with user approval. |
| **Model independence** | Different models for implementation vs. audit. Don't grade your own homework. |
| **Belt-and-suspenders** | Agents run gates internally; orchestrator re-runs as hard external gate. |
| **Staleness over limits** | Detect no-progress (plan.md unchanged) rather than fixed iteration caps. Max cycles is a safety net. |
| **Evidence-based signposts** | Require exact errors/output, not conclusions. Prevents misinformation across invocations. |
| **Cross-reference before fix** | Auditors check signposts before adding fix items. Prevents audit-task undoing resolved work (ping-pong). |
| **Self-healing** | Orchestrator fixes recoverable issues (spec.md reverted, checkboxes persisted) instead of aborting. |
| **Standards as long-term memory** | Standards persist across specs. Signposts/audit-logs are per-spec. walk-spec evaluates promotion via `/discover-standards`. |
| **Human at the boundaries** | Interactive bookends (shape-spec, walk-spec) + edge-case touchpoints (handle-feedback, resolve-blockers). Automated commands never override human choices. |

---

## Appendix: File Format Reference

<details>
<summary>spec.md format</summary>

```markdown
spec_id: sX.Y.ZZ
issue: https://github.com/OWNER/REPO/issues/NNN
version: vX.Y

# Spec: [Title]

## Problem
[Brief statement]

## Goals
- [Goal 1]
- [Goal 2]

## Non-Goals
- [Exclusion 1]

## Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any are violated:

1. **[Non-negotiable 1]** -- [explanation]
2. **[Non-negotiable 2]** -- [explanation]
```

</details>

<details>
<summary>plan.md format</summary>

```markdown
spec_id: sX.Y.ZZ
issue: https://github.com/OWNER/REPO/issues/NNN
version: vX.Y

# Plan: [Title]

## Decision Record
[Brief rationale]

## Tasks
- [x] Task 1: Save Spec Documentation
- [ ] Task 2: [Description]
  - [Concrete step]
  - [Referenced file]
  - [Test expectation]
- [ ] Task N: [Last task]
```

When audit-task finds issues:
```markdown
- [ ] Task 6: Use OpenRouterModel for OpenRouter endpoints
  - [ ] Fix: Missing type annotation on routing_settings field (audit round N)
  - [ ] Fix: Dead import of PromptedOutput in runtime.py:3 (audit round N)
```

When handle-feedback adds items:
```markdown
- [ ] Fix: [description] (PR #NNN feedback from @author, feedback round N)
```

Task 1 must be "Save Spec Documentation". No tasks for verification gates.

</details>

<details>
<summary>demo.md format</summary>

```markdown
# Demo: [Title]

[Narrative intro]

## Steps

1. [Action] -- expected: [outcome]
2. [Action] -- expected: [outcome]

## Results

(Appended by run-demo)
```

Results per run:
```markdown
### Run N -- [context] (YYYY-MM-DD HH:MM)
- Step 1: PASS|FAIL -- [note]
- Step 2: PASS|FAIL -- [note]
- **Overall: PASS|FAIL**
```

</details>

<details>
<summary>signposts.md format</summary>

Header (created on first use):
```markdown
# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.**

---
```

Each entry includes:
- **Task:** which task number
- **Status:** `unresolved` | `resolved` | `deferred`
- **Problem:** what went wrong
- **Evidence:** exact error, command output, or code snippet
- **Tried:** what was attempted
- **Solution:** what worked (or "unresolved")
- **Resolution:** who/what resolved it and when (omit if unresolved)
- **Files affected:** which files

From run-demo, also: **Root cause**. From audit-task, also: **Impact**.

</details>

<details>
<summary>audit-log.md format</summary>

Header:
```markdown
# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---
```

Entry formats:
```markdown
- **Task N** (round R): PASS|FAIL -- [summary]
- **Demo** (run N): PASS|FAIL -- [summary]
- **Spec Audit** (round N): PASS|FAIL -- [rubric summary, fix-now count]
- **Feedback** (round N): {count} items -- {valid} actionable, {addressed} addressed, {invalid} invalid, {deferred} out-of-scope
```

</details>

<details>
<summary>audit.md format</summary>

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

## Demo Status
- Latest run: PASS|FAIL (Run N, date)

## Standards Adherence
- [Standard]: [PASS|violation with file:line]

## Regression Check
- [Findings]

## Action Items

### Fix Now
- [Item with file:line]

### Deferred
- [Item] -> [GitHub issue URL]
```

**Status rules:** `pass` requires all rubric 5/5, all non-negotiables PASS, demo PASS, zero Fix Now. Otherwise `fail`.

</details>

<details>
<summary>standards index.yml format</summary>

```yaml
folder-name:
  file-name:
    description: Brief description here
```

Rules: alphabetize folders, alphabetize files within folders, no `.md` extension, one-line descriptions. `root` = files directly in `agent-os/standards/`.

</details>
