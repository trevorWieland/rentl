# Audit Spec

Critique and score completed spec implementations across a 5-pronged rubric (Performance, Intent, Completion, Security, Stability) plus standards adherence. Produces an audit.md file in the spec folder.

## Important Guidelines

- Always use AskUserQuestion tool when asking the user anything
- Be thorough but focused - audit what matters most
- Be specific in citations - point to exact files, lines, and issues
- Offer constructive feedback - issues should be actionable
- **Key workflow difference from shape-spec:** The AI agent performs all assessments autonomously, then presents action items to user for decision-making

## Prerequisites

This command assumes:

1. A completed spec folder exists in `agent-os/specs/` with:
   - `plan.md` - The implementation plan
   - `shape.md` - Shaping decisions and context
   - `standards.md` - Standards that apply to this work

2. The implementation is complete:
   - Code has been written for all tasks in plan.md
   - Tests pass (`make all` succeeds)
   - The implementation can run

If these prerequisites are not met, stop and inform the user what's needed before proceeding.

## Process

### Step 1: Identify Spec to Audit (First Run) or Review Existing Audit (Subsequent Runs)

**For first audit run on a spec:**

**Step 1a: Attempt to resolve spec from user's request**

First, examine the user's initial command/request for any spec identifiers. Look for:
- Full folder names (e.g., "2026-01-26-1449-export-adapter")
- Date portions (e.g., "1449", "2026-01-26")
- Slug portions (e.g., "export-adapter", "export", "adapter")
- Feature names (e.g., "export adapter", "scaffolding", "schemas")

List all spec folders in `agent-os/specs/` and match against the user's request:

1. **Exact match**: If the user's text matches a folder name exactly, use it
2. **Slug match**: If the user's text matches the slug portion (after the timestamp), use it
3. **Partial match**: If the user's text appears in the folder name (case-insensitive), consider it a match
4. **Fuzzy match**: If the user mentions related keywords (e.g., "import" matches "import-adapter"), consider it a match

**Step 1b: Proceed based on match results**

- **If exactly one spec matches**: Proceed immediately with that spec. Briefly confirm:
  ```
  Found spec: 2026-01-26-1449-export-adapter
  Proceeding with audit...
  ```

- **If multiple specs match**: Use AskUserQuestion to disambiguate:
  ```
  Multiple specs match your request. Which one?

  1. 2026-01-26-1223-import-adapter
  2. 2026-01-26-1449-export-adapter

  (Pick a number)
  ```

- **If no specs match**: Use AskUserQuestion with the full list:
  ```
  Which spec would you like to audit?

  1. 2026-01-25-1100-rentl-repo-scaffolding
  2. 2026-01-25-1200-pydantic-schemas-validation
  3. 2026-01-25-1937-progress-semantics-tracking
  4. 2026-01-26-1223-import-adapter
  5. 2026-01-26-1449-export-adapter
  ... [list all available specs]

  (Pick a number or specify a custom path)
  ```

Let the user select from the list or provide a custom path.

**For subsequent audit runs:**

1. Check if `audit.md` exists in the spec folder
2. If yes, read the existing `audit.md` first
3. Verify all previous action items were addressed by checking the files/lines mentioned
4. Mark addressed items as "Resolved" and carry forward unresolved items
5. Note this is Audit Run #N in the audit history

### Step 2: Gather Implementation Context

Read and analyze the following documents:

**Spec documents:**
- `agent-os/specs/{folder-name}/plan.md` - Implementation plan with task list
- `agent-os/specs/{folder-name}/shape.md` - Scope, decisions, context
- `agent-os/specs/{folder-name}/standards.md` - Standards that apply

**Product context:**
- `agent-os/product/mission.md` - Product goals and user personas
- `agent-os/product/roadmap.md` - Phases and features

**Implementation files:**
- Identify which packages were modified based on the plan
- List the main implementation files to review

**Test coverage:**
- Check if tests exist in `tests/unit/`, `tests/integration/`, or `tests/quality/`
- Run `make test` or `pytest` if needed to verify test results
- Check coverage if available

Use AskUserQuestion only if clarification is needed:

```
I've identified these implementation files from the plan:
- packages/rentl-schemas/src/rentl_schemas/primitives.py
- packages/rentl-io/src/rentl_io/ingest/csv_adapter.py
- tests/unit/io/test_ingest_adapters.py

Are there any additional files I should review?
```

### Step 3: Perform Comprehensive Audit (Autonomous)

The AI agent performs all assessments autonomously without user intervention.

Take your time to do a thorough review. Read implementation files, check against standards, and compile findings.

**Performance Assessment (Score 1-5):**

Evaluate for:

- **Blocking I/O:** File operations, network calls, or other I/O in async functions
- **Missing async:** Synchronous code that should be async for parallel execution
- **Inefficient algorithms:** O(n²) where O(n) would work, unnecessary loops
- **Memory issues:** Loading entire files into memory when streaming would work
- **N+1 queries:** Database patterns that could be batched
- **Caching:** Missing caching where appropriate

Identify specific file:line citations for any issues found.

Document positive observations too - acknowledge good patterns when you see them.

Score: 1=critical issues, 2=significant issues, 3=moderate issues, 4=minor issues, 5=excellent

**Intent Assessment (Score 1-5):**

Evaluate:

- **Spec alignment:** Does the implementation match what was specified in plan.md?
- **Product goals:** Does it align with mission.md and roadmap.md?
- **User needs:** Does it solve the intended user problem?
- **Misalignment:** Is there confusion about what the spec was meant to accomplish?

Check against the spec's scope and decisions in shape.md.

Identify any misalignment or confusion about spec purpose.

Score: 1=misaligned, 2=poor alignment, 3=acceptable alignment, 4=good alignment, 5=perfect alignment

**Completion Assessment (Score 1-5):**

Evaluate:

- **Task completion:** Check against plan.md task list - is every task done?
- **Deliverables:** Do all expected files, functions, classes exist?
- **Tests:** Are tests present for all production code?
- **Docs:** Is documentation present where needed?

For each task in plan.md, verify:
- Code exists and is implemented
- Tests exist and pass
- Documentation is updated if required

Identify what's complete and what's missing.

Score: 1=incomplete (critical gaps), 2=mostly incomplete, 3=partially complete, 4=nearly complete, 5=fully complete

**Security Assessment (Score 1-5):**

Evaluate for:

- **Injection vulnerabilities:** SQL injection, command injection, path traversal
- **Credential exposure:** Hardcoded secrets, keys in code, logging sensitive data
- **Unsafe inputs:** Missing validation, unsanitized user input
- **Dependency vulnerabilities:** Outdated packages with known CVEs
- **Authentication/authorization:** Missing auth checks, improper permission handling
- **Data leakage:** Sensitive data in logs, debug data in production

Check for common security patterns:
- Input validation before processing
- Parameterized queries instead of string concatenation
- Proper error handling that doesn't leak stack traces

Score: 1=critical vulnerabilities, 2=significant security issues, 3=moderate concerns, 4=minor concerns, 5=secure

**Stability Assessment (Score 1-5):**

Evaluate for:

- **Error handling:** Are exceptions caught and handled appropriately?
- **Race conditions:** Shared state access without locks or atomic operations
- **Resource leaks:** Unclosed files, database connections, network sockets
- **Flakey behavior:** Non-deterministic code, timing-dependent issues
- **Edge cases:** Empty inputs, None values, boundary conditions
- **Idempotency:** Can operations be safely retried?

Check for:
- Try/except blocks that are too broad
- Missing cleanup (no finally blocks or context managers)
- Timeout handling for network operations
- Retry logic with exponential backoff

Score: 1=unreliable, 2=significant reliability issues, 3=moderate concerns, 4=minor concerns, 5=rock solid

**Standards Adherence Review:**

For each standard listed in the spec's `standards.md`:

1. Read the standard file from `agent-os/standards/`
2. Check the implementation against each rule in the standard
3. Identify violations with specific file:line citations
4. Quote the violated rule for clarity

Group violations by standard name.

List all standards that are compliant (no violations found).

**Action Item Compilation:**

Compile all issues from all assessments into action items.

Each action item must include:
- **Description:** Clear, concise description of the issue
- **Location:** File path with line number (e.g., `packages/rentl-io/src/rentl_io/ingest/csv_adapter.py:45`)
- **Category:** Performance, Intent, Completion, Security, Stability, or Standards
- **Priority:** High, Medium, or Low
  - **High:** Blocks functionality, critical security issues, or major spec violations
  - **Medium:** Important but not blocking, or quality improvements
  - **Low:** Nice to have, minor optimizations, or style issues

Group action items by category for presentation.

### Step 4: Categorize Action Items with User

Present each action item to the user for categorization. **The audit command only categorizes and documents issues—it does not fix them.** Fixes are addressed by running the `fix-spec` command after the audit is complete.

For each action item, use AskUserQuestion to present it with context:

```
Action Item 1 of 5:

[Category: Performance] Blocking file I/O in async function
Location: packages/rentl-io/src/rentl_io/ingest/csv_adapter.py:45

Issue: Uses blocking open() instead of asyncio.to_thread()

The python/async-first-design standard requires: "All I/O operations (LLM calls, storage, vector store, file IO) use async/await"

Priority: High

How should this action item be handled?
1. Add to current spec (will be fixed by running /fix-spec)
2. Defer to future spec (will be added to roadmap now)
3. Ignore (will be documented with your reasoning)

(Choose 1, 2, or 3)
```

Wait for the user's response before moving to the next action item.

**Handle each choice as follows:**

#### Choice 1: Add to Current Spec

Log the item in audit.md under "Add to Current Spec (Fix Now)". The user will run `/fix-spec` after the audit to address these items.

#### Choice 2: Defer to Future Spec

When user selects "Defer":

1. Read `agent-os/product/roadmap.md` to identify available milestones
2. Use AskUserQuestion to ask which milestone:
   ```
   This item will be deferred to the roadmap. Which milestone should it be added to?

   1. v0.1: Playable Patch
   2. v0.2: Quality Leap
   3. v0.3: Scale & Ecosystem
   4. v0.4: UX Polish
   5. v1.0: Professional-Grade Tooling
   6. Post-v1.0 Future Directions

   (Pick a number)
   ```
3. Append the item to the selected milestone's scope section in `roadmap.md`
4. Log the deferral in `audit.md` with the target milestone noted

#### Choice 3: Ignore

When user selects "Ignore":

1. Use AskUserQuestion to capture the rationale:
   ```
   Why are we ignoring this item?

   (Provide a brief reason for the record)
   ```
2. Log the item in `audit.md` under "Ignore" with the user's reasoning

Present all action items before generating the audit report.

### Step 5: Generate audit.md

After all action items have been presented and categorized, create `agent-os/specs/{folder-name}/audit.md` with the following structure:

```markdown
# {Spec Name} — Audit Report

**Audited:** YYYY-MM-DD
**Spec:** agent-os/specs/{folder-name}/
**Implementation Status:** Complete

## Overall Assessment

**Weighted Score:** {average of 5 rubric scores}/5.0
**Status:** Pass / Conditional Pass / Fail

**Summary:**
[Brief 2-3 sentence summary of overall quality and readiness]

## Performance

**Score:** X/5

**Findings:**
- [Specific issues with file:line citations, or "No issues found"]
- [Positive observations and good practices]

## Intent

**Score:** X/5

**Findings:**
- [Alignment with product goals and spec intent]
- [Any concerns or clarifications needed]

## Completion

**Score:** X/5

**Findings:**
- [What's complete and working well]
- [What's missing or incomplete, if anything]

## Security

**Score:** X/5

**Findings:**
- [Security concerns with file:line citations, or "No issues found"]
- [Best practices observed]

## Stability

**Score:** X/5

**Findings:**
- [Reliability concerns with file:line citations, or "No issues found"]
- [Error handling observations and good practices]

## Standards Adherence

### Violations by Standard

#### {standard-name}
- `{file}:{line}` - [description of violation]
  - Standard requires: "[quote the violated rule]"

#### {another-standard-name}
- No violations found

### Compliant Standards

- {standard-name} ✓
- {another-standard-name} ✓
- ...

## Action Items

### Add to Current Spec (Fix Now)

These items will be addressed by running `/fix-spec`.

1. [Priority: High] {description}
   Location: {file}:{line}
   Reason: {standard reference or category explanation}

2. [Priority: Medium] {description}
   Location: {file}:{line}
   Reason: {standard reference or category explanation}

### Defer to Future Spec

These items have been added to the roadmap.

3. [Priority: Low] {description}
   Location: {file}:{line}
   Deferred to: {milestone name}
   Reason: {category explanation}

### Ignore

These items were reviewed and intentionally not actioned.

- {description}
  Location: {file}:{line}
  Reason: {user's rationale for ignoring}

### Resolved (from previous audits)
- None (or list of items from previous audits that were addressed)

## Final Recommendation

**Status:** Pass / Conditional Pass / Fail

**Reasoning:**
[Detailed explanation of the decision]

- If **Pass**: All rubric scores are 4+ and no high-priority action items
- If **Conditional Pass**: Scores are acceptable (3+) but have actionable improvements
- If **Fail**: Critical issues (score <3, security vulnerabilities, or incomplete implementation)

**Next Steps:**
[Specific guidance on what's needed to reach full approval]
```

If this is a subsequent audit run (not the first), also include:

```markdown
## Audit History

### {YYYY-MM-DD} (Audit Run #{N})
- Previous scores: {list of scores}
- New scores: {list of scores}
- Standards violations: {old count} → {new count}
- Action items: {old count} → {new count}
- Key changes: {brief summary of what improved}

### {YYYY-MM-DD} (Audit Run #{N-1})
- Initial audit
- Scores summary
- Action items created
```

### Step 6: Final Summary to User

After generating audit.md, provide a summary to the user:

```
Audit complete! Report saved to: agent-os/specs/{folder-name}/audit.md

Summary:
- Overall score: X/5
- Status: Pass / Conditional Pass / Fail
- Action items to fix: N (run /fix-spec to address)
- Action items deferred: M (added to roadmap)
- Action items ignored: P (documented with reasoning)

[If status is Conditional Pass or Fail]
To reach full approval:
1. Run /fix-spec to address the N "Fix Now" items
2. Run /audit-spec again to verify fixes
3. Repeat until all scores are 5/5 with no action items

[If status is Pass]
This spec is ready for the next phase!
```

## audit.md Output Format

The audit.md file should be clean, well-formatted, and include all sections above.

Key formatting rules:
- Use consistent heading levels (## for main sections, ### for subsections)
- Use bullet points for lists
- Include file:line citations in backticks
- Use ✓ for compliant standards
- Separate sections with blank lines
- Keep descriptions concise but informative

## Tips

- **Focus on what matters most** - don't audit everything equally. Security and Stability are typically more critical than minor performance optimizations.
- **Be specific in citations** - file:line is essential for actionable feedback. Without it, developers can't find the issue.
- **Balance critique with recognition** - acknowledge good work alongside issues. A score of 4/5 with good observations is still strong.
- **If score is low in a category**, provide clear guidance on how to improve. Don't just say "this is bad" - explain how to fix it.
- **Standards violations should reference the specific standard** and quote the violated rule. This makes it clear what to change.
- **Use conditional pass when issues exist but are non-blocking**. Examples: minor performance optimizations, low-priority stability concerns, style issues.
- **Use fail only when critical issues prevent implementation from being usable**. Examples: security vulnerabilities, incomplete features, crashes, data loss.
- **On subsequent runs, carry forward unresolved action items** - don't let them get lost in the noise. Check if previous items were addressed.
- **The goal is an audit with all 5s and no action items** - that's the gate to moving to the next spec.

## Integration with Existing Workflow

Position this command in the development lifecycle:

1. **Run AFTER implementation is complete and tests pass**
   - `make all` should succeed
   - All tasks from plan.md should be implemented
   - Tests should be passing

2. **Run BEFORE merging or moving to the next spec**
   - Acts as a quality gate
   - Ensures implementation meets project standards
   - Provides documented record of review

3. **Enables iterative improvement with fix-spec**
   - Run audit-spec to identify and categorize issues
   - Run fix-spec to address "Fix Now" items
   - Run audit-spec again to verify fixes
   - Repeat until all scores are 5/5 with no action items

4. **The full workflow**
   ```
   shape-spec → audit-spec → fix-spec → audit-spec → (repeat) → all green
   ```

## Workflow Summary

1. User runs audit-spec
2. AI identifies spec (first run) or reviews existing audit.md (subsequent)
3. AI gathers context, reads all spec/docs, does deep code review
4. AI autonomously scores all 5 categories + checks standards
5. AI compiles action items with file:line citations
6. AI presents each action item to user for categorization:
   - **Add to Current Spec** → Logged for fix-spec to address
   - **Defer to Future Spec** → Added to roadmap at user-selected milestone
   - **Ignore** → Logged with user's reasoning
7. AI generates audit.md with all findings, scores, and user decisions
8. Audit is saved; user runs fix-spec to address "Fix Now" items
9. User re-runs audit-spec to verify fixes; repeat until all green

**Success criteria:** All rubric scores are 5/5 and no action items remain in "Add to Current Spec"
