# Contributing

Thanks for helping build rentl. This repo uses a spec-driven workflow powered by Agent OS — a set of agent commands and an orchestrator that automate implementation, auditing, and demo validation.

## Prerequisites

Install these before working on the project:

| Tool | Version | Purpose |
|------|---------|---------|
| Python | >= 3.14 | Runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Package and workspace manager |
| [gh](https://cli.github.com/) | latest | GitHub CLI (issues, PRs, branches) |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | latest | Agent CLI for running commands (`claude -p` for headless) |
| make | any | Verification gates |
| bash | >= 4.0 | Orchestrator script |

## Quick Start

```bash
# Install dependencies
make install

# Run the quick verification gate (format, lint, type, unit tests)
make check

# Run the full verification gate (adds integration + quality tests)
make all
```

## Verification Gates

Two tiers of verification, used at different points in the workflow:

| Gate | Command | What it runs | When it's used |
|------|---------|--------------|----------------|
| Task gate | `make check` | format, lint, typecheck, unit tests | After each task implementation |
| Spec gate | `make all` | format, lint, typecheck, unit, integration, quality | After all tasks complete, before demo |

Individual targets are also available: `make format`, `make lint`, `make type`, `make unit`, `make integration`, `make quality`.

## Agent OS Workflow (v2)

All agent commands live in `.claude/commands/agent-os/`. The workflow has two interactive bookends (human + agent) with a fully automated middle:

```
shape-spec (interactive)
    |
    v
 +--------------------------------------------------------------+
 |  orchestrate.sh (automated)                                   |
 |                                                               |
 |  for each unchecked task:                                     |
 |      do-task  -->  make check (gate)  -->  audit-task         |
 |                                                               |
 |  make all (gate)                                              |
 |  run-demo  -->  if issues: adds tasks, loops back             |
 |                                                               |
 |  audit-spec  -->  if issues: adds tasks, loops back           |
 |               -->  if pass: notify human                      |
 +--------------------------------------------------------------+
    |
    v
walk-spec (interactive)  -->  PR
```

### Commands

| Command | Mode | Purpose |
|---------|------|---------|
| `/shape-spec` | Interactive (TUI) | Plan the work with the user. Produces spec.md, plan.md, demo.md, standards.md, references.md. Creates branch, commits spec docs, pushes. |
| `/do-task` | Automated (headless) | Implements one task per invocation. Reads plan.md for the next unchecked task, implements it, runs `make check`, commits. |
| `/audit-task` | Automated (headless) | Audits the most recently completed task. Checks against spec.md non-negotiables and standards. Unchecks task and adds fix items if issues found. |
| `/run-demo` | Automated (headless) | Executes the demo plan from demo.md. If steps fail, investigates root cause and adds fix tasks to plan.md. |
| `/audit-spec` | Automated (headless) | Bird's-eye audit of the full implementation. 5-prong rubric, non-negotiable compliance, regression detection. Writes audit.md with machine-readable status. |
| `/walk-spec` | Interactive (TUI) | Human validation checkpoint. Walks the user through the demo, submits PR, updates roadmap. |

Deprecated commands (`/do-spec`, `/fix-spec`) redirect to `/do-task`.

### Running the Workflow

**Step 1: Shape the spec (interactive)**

```bash
# In Claude Code TUI, enter plan mode then run:
/shape-spec
```

This creates the spec folder, branch, and all planning artifacts.

**Step 2: Run the orchestrator (automated)**

```bash
./agent-os/scripts/orchestrate.sh agent-os/specs/<your-spec-folder>
```

The orchestrator loops through all tasks, runs verification gates, executes the demo, and performs the spec audit. It stops when everything passes or when it detects staleness (no progress between cycles).

**Step 3: Walk and submit (interactive)**

```bash
# In Claude Code TUI:
/walk-spec
```

This walks you through the demo, submits the PR, and updates the roadmap.

### Orchestrator Configuration

The orchestrator accepts configuration via environment variables or a config file:

```bash
# Environment variables
ORCH_CLI="claude -p"           # Headless agent CLI command
ORCH_DO_MODEL=""               # Model for do-task (empty = CLI default)
ORCH_AUDIT_MODEL=""            # Model for audit-task
ORCH_DEMO_MODEL=""             # Model for run-demo
ORCH_SPEC_MODEL=""             # Model for audit-spec
ORCH_TASK_GATE="make check"   # Task-level verification command
ORCH_SPEC_GATE="make all"     # Spec-level verification command
ORCH_MAX_CYCLES=10            # Safety limit (staleness detector is primary)

# Or use a config file
./agent-os/scripts/orchestrate.sh <spec-folder> --config my-config.conf
```

## Spec Folder Structure

Each spec lives in `agent-os/specs/{YYYY-MM-DD-HHMM-spec_id-feature-slug}/`:

| File | Mutability | Purpose |
|------|------------|---------|
| `spec.md` | **Immutable** | Acceptance criteria, non-negotiables, Note to Code Auditors |
| `plan.md` | Mutable | Checklist tasks (`[ ]`/`[x]`), fix items added by audits |
| `demo.md` | Plan: immutable, Results: append-only | Narrative demo plan + recorded results per run |
| `standards.md` | Static | Applicable standards for this spec |
| `references.md` | Static | Implementation files, issues, related specs |
| `signposts.md` | Append-only | Problems encountered with mandatory evidence |
| `audit-log.md` | Append-only | Running history of task audits, demo runs, spec audits |
| `audit.md` | Overwritten per audit | Latest spec audit with machine-readable `status:` header |

Key invariant: **spec.md is never modified by automated commands.** If an agent modifies spec.md, that's a bug.

## GitHub Issues and Spec IDs

GitHub is the source of truth for spec IDs.

When creating a new spec:
- Check GitHub for the next available `spec_id` in the target version.
- Use labels: `type:spec`, `status:planned`, `version:vX.Y`.

To align local roadmap with GitHub:
- Run `/sync-roadmap`.

## Branching and PRs

- `shape-spec` creates the branch (via `gh issue develop`) and pushes it.
- All implementation happens on this branch with one commit per task.
- `walk-spec` submits the PR and pushes final changes.

## Other Agent Commands

| Command | Purpose |
|---------|---------|
| `/plan-product` | Establish product docs (mission, roadmap, tech stack) |
| `/inject-standards` | Inject relevant coding standards into context |
| `/discover-standards` | Discover new standards from codebase patterns |
| `/index-standards` | Rebuild the standards index |
| `/sync-roadmap` | Sync local roadmap with GitHub issues |

## Questions

If you are unsure about the workflow or where to start, open an issue and tag it with `type:spec` or ask in an existing spec issue thread.
