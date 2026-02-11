# Shape Spec

Plan the work with the user. Produce all spec artifacts and push. This is the only command where the user and agent collaborate interactively on what to build.

**Suggested model:** Strong planner with good communication skills (e.g., Opus via TUI).

## Important Guidelines

- Always use AskUserQuestion tool when asking the user anything
- Offer suggestions — present options the user can confirm or adjust
- Keep it lightweight — this is shaping, not exhaustive documentation
- Prefer GitHub issues as the source of truth for spec id, title, status, and dependencies
- spec.md is the immutable contract — get it right here, because no automated command will change it

## Prerequisites

Steps 1–11 are discussion only — do NOT create branches, write files, or run git commands until Step 12.

## Process

### Step 1: Resolve the Spec Issue

If the user provided an issue number, URL, or spec id:

1. Fetch the issue via `gh issue view` to get title, body, labels, milestone, and relationships.
2. Extract `spec_id`, `version` (from `version:*` label), and dependencies (blocked-by relationships).

If no issue was provided, use AskUserQuestion:

```
Do you want me to create a new spec issue on GitHub before shaping?

1. I have an existing issue
2. Create a new issue now
3. Pick the next best issue from the roadmap
```

If picking the next best issue:

1. Run the candidate finder script — it resolves dependency chains and shows only the earliest milestone:

```
python3 agent-os/scripts/list-candidates.py
```

2. Present the candidates to the user with AskUserQuestion. Do NOT do any additional research, exploration, or codebase analysis at this point — just show the script output and let the user pick.
3. Once chosen, fetch the full issue with `gh issue view <number>`.

If using an existing issue:

1. Ask for the issue number or URL.

If creating a new issue:

1. Determine the next available `spec_id` by scanning GitHub issues for the target version.
2. Create the issue with labels `type:spec`, `status:planned`, `version:vX.Y` and set the milestone.
3. Use the new issue as the shaping context.

### Step 2: Clarify Scope

Use the issue title/body as the primary scope. Ask only if unclear:

```
I pulled scope from the issue. Any constraints or expected outcomes I should add?
```

### Step 3: Gather Visuals (Optional)

```
Any visuals to reference? (mockups, screenshots, examples, or "none")
```

### Step 4: Reference Implementations (Optional)

```
Is there similar code in this codebase I should reference? (paths or "none")
```

### Step 5: Product Context (Quick Alignment)

If `agent-os/product/` exists, skim key files and ask:

```
Any product goals or constraints this spec should align with?
```

### Step 6: Standards

Read `agent-os/standards/index.yml` and propose relevant standards. Confirm with AskUserQuestion.

### Step 7: Non-Negotiables

Non-negotiables are the things auditors must never compromise on. They go into spec.md under **Note to Code Auditors** and are checked by every audit command in the lifecycle.

Work with the user to define these. Propose based on the scope and ask for confirmation. Good non-negotiables are:

- **Specific** — not "code should be clean" but "no dict[str, Any] in routing config"
- **Verifiable** — an auditor can check pass/fail with evidence
- **Important** — things that, if violated, mean the feature is fundamentally broken

Example:

```
Here are proposed non-negotiables for this spec:

1. No mixed output modes — the runtime must use tool output exclusively
2. All routing config must use typed Pydantic models
3. No test deletions or modifications to make audits pass

Would you adjust any of these?
```

### Step 8: Define Acceptance Criteria

Draft acceptance criteria for spec.md. These are the contract — they define when the spec is done. Each criterion should be:

- **Observable** — can be verified by reading code or running a command
- **Scoped** — tied to this spec, not general quality
- **Complete** — if all criteria pass, the feature works

Present to the user for confirmation.

### Step 9: Demo Plan

Every spec must include a demo plan in demo.md. The demo is the chance to prove the feature works interactively — not through passing tests, but by actually using the feature the way a user would.

Write the demo plan as if you're pitching the feature to someone who knows nothing about the implementation. Start with what the feature is and why it matters, then describe how you'll prove it works.

Example framing (adapt to the feature):

```
The project now works whether you use local models or a cloud provider.
In this demo, we'll prove how both work, how to switch between them,
and why this matters for reliability.

1. Run the pipeline with the default local provider — show it completes.
2. Switch the config to the cloud provider — show the same pipeline completes.
3. Show the logs confirming the correct provider routing.
```

#### 9a: Environment Assessment

Before finalizing the demo steps, assess the execution environment with the user. The goal is to determine **upfront** which steps the autonomous `run-demo` agent can actually execute, so it doesn't have to guess later.

Ask using AskUserQuestion:

```
For the autonomous demo runner, what's available in the execution environment?
- API keys / credentials: [e.g., OPENROUTER_API_KEY in .env, no GCP credentials]
- External services: [e.g., OpenRouter API reachable, no GPU cluster]
- Hardware / resources: [e.g., 16GB RAM, no GPU]
- Special setup needed: [e.g., "run make seed first", or "none"]

Based on this, here's how I'd classify each demo step:
1. **[RUN]** Download eval set — no external dependencies
2. **[RUN]** Run pipeline with model X — API key available via .env
3. **[VERIFY]** Run on GPU cluster — no GPU available; verify via [alternative]

Does this look right?
```

Classify each step as:

- **[RUN]** — The step will be executed by the autonomous demo agent. This is the default. Use this unless there's a concrete reason the step cannot run.
- **[VERIFY]** — The step cannot be executed autonomously due to a documented environment limitation. Must include what will be verified instead and why. This is the exception — use sparingly.

The classification is written into demo.md and becomes binding for `run-demo`. The agent does not get to reclassify steps at execution time.

#### 9b: Finalize Demo Plan

Propose the demo and confirm with AskUserQuestion:

```
Here's my proposed demo for this feature:
[demo plan with [RUN]/[VERIFY] tags]
Does this cover what matters, or would you adjust it?
```

Demo plan qualities:

- **Narrative** — opens with what the feature is and why it matters
- **Concise** — a focused proof, not an exhaustive test suite
- **Specific** — concrete actions and observable outcomes
- **Accessible** — someone unfamiliar with the implementation could follow it
- **Medium-agnostic** — CLI, TUI, web UI, config changes, API calls, whatever fits
- **Executable by default** — most steps should be [RUN]; [VERIFY] requires justification

The demo plan is used by every subsequent command:
- `run-demo` (via orchestrator) executes [RUN] steps and verifies [VERIFY] steps
- `audit-spec` verifies the demo was run and passed
- `walk-spec` walks the user through the demo interactively

### Step 10: Task Plan

Structure the implementation as a checklist in plan.md. Use the demo plan to inform what tests are needed — the test suite should guarantee the demo will pass.

Task 1 must always be **Save Spec Documentation** (shape-spec completes this task during the commit step — see Step 12). The final task should be the last implementation task. Do not add a task for running the verification gate — the orchestrator handles that automatically.

Plan quality requirements:

- Each task includes concrete steps and referenced files (paths or modules)
- Include test expectations per task where relevant
- Add acceptance checks tied to user value

Think backwards from the demo: what would need to be tested to guarantee each demo step succeeds?

Present the plan to the user for confirmation.

### Step 11: Spec Folder Name

Create:

```
YYYY-MM-DD-HHMM-{spec_id}-{feature-slug}/
```

### Step 12: Create Branch, Save Spec Docs, Commit, and Push

1. Create the issue branch via `gh issue develop` and check it out.
2. Create the spec folder and write all spec files:
   - `spec.md` — acceptance criteria, non-negotiables, Note to Code Auditors (this is the immutable contract)
   - `plan.md` — checklist tasks, decision record, metadata
   - `demo.md` — narrative demo plan
   - `standards.md` — applicable standards list
   - `references.md` — implementation files, issues, related specs
   - Any visuals in `visuals/`
3. Check off Task 1 in plan.md: `[ ]` → `[x]` for "Save Spec Documentation" — this task is now complete.
4. Commit **only** the spec docs on the issue branch.
5. Update the **issue body** (do not post a new comment) with a "Spec Summary" section that includes:
   - Spec folder path
   - Plan summary (tasks and acceptance checks)
   - Non-negotiables
   - References and standards applied
6. Push the branch with `-u` to publish it.

### Step 13: Stop and Handoff

Do not start implementation. The orchestrator handles everything from here.

Next step: run the orchestrator script, which invokes `do-task`, `audit-task`, `run-demo`, and `audit-spec` automatically.

## Output Structure

```
agent-os/specs/{YYYY-MM-DD-HHMM-spec_id-feature-slug}/
├── spec.md          # Acceptance criteria, non-negotiables (IMMUTABLE)
├── plan.md          # Checklist tasks, decision record (MUTABLE)
├── demo.md          # Demo plan (plan section immutable, results appended later)
├── standards.md     # Applicable standards list
├── references.md    # Implementation files, issues, related specs
└── visuals/         # Optional mockups, diagrams, screenshots
```

## File Format: spec.md

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

1. **[Non-negotiable 1]** — [explanation]
2. **[Non-negotiable 2]** — [explanation]
```

## File Format: plan.md

```markdown
spec_id: sX.Y.ZZ
issue: https://github.com/OWNER/REPO/issues/NNN
version: vX.Y

# Plan: [Title]

## Decision Record
[Why this work exists — brief rationale]

## Tasks
- [ ] Task 1: Save Spec Documentation
- [ ] Task 2: [Description]
  - [Concrete step]
  - [Referenced file or module]
  - [Test expectation]
- [ ] Task 3: [Description]
  ...
- [ ] Task N: [Last implementation task]
```

## File Format: demo.md

```markdown
# Demo: [Title]

[Narrative intro — what the feature is, why it matters]

## Environment

- API keys: [what's available, e.g., "OPENROUTER_API_KEY via .env"]
- External services: [what's reachable, e.g., "OpenRouter API"]
- Setup: [any pre-demo setup, or "none"]

## Steps

1. **[RUN]** [Action] — expected: [observable outcome]
2. **[RUN]** [Action] — expected: [observable outcome]
3. **[VERIFY]** [Action] — expected: [observable outcome] — verify: [what to check instead and why this can't be run]

## Results

(Appended by run-demo — do not write this section during shaping)
```

Step classification rules:
- **[RUN]** is the default. The autonomous demo agent MUST execute these steps.
- **[VERIFY]** means the step cannot run due to a documented environment limitation. The agent verifies indirectly but cannot claim PASS for it — it reports VERIFIED with what was checked.
- Classifications are set during shape-spec and are binding. run-demo does not reclassify.

## Workflow

```
shape-spec → [orchestrator: do-task ↔ audit-task loop → run-demo → audit-spec] → walk-spec → PR
```

Next step after this command: run the orchestrator.
