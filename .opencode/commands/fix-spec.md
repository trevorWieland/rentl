---
description: Address action items from an audit that were marked "Add to Current Spec (Fix Now)".
---

# Fix Spec

This command reads the audit.md, fixes each issue at the cited location, and verifies the fix with `make all`.

## Important Guidelines

- **Autonomous execution** — User already approved these items during audit; fix without re-asking
- **Be thorough but focused** — Address exactly what the action item describes
- **Verify after fixing** — Run `make all` to ensure fixes don't break the build
- **Report progress** — Summarize what was fixed and what remains

## Prerequisites

This command assumes:

1. A completed spec folder exists in `agent-os/specs/` with:
   - `audit.md` - The audit report with action items

2. The audit has been run at least once:
   - `audit.md` exists and contains action items
   - Action items have been categorized by the user

3. There are items marked "Add to Current Spec (Fix Now)":
   - If no "Fix Now" items exist, inform the user and exit

If these prerequisites are not met, stop and inform the user what's needed before proceeding.

## Process

### Step 1: Identify Spec to Fix

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
  Proceeding with fix...
  ```

- **If multiple specs match**: Use question to disambiguate:
  ```
  Multiple specs match your request. Which one?

  1. 2026-01-26-1223-import-adapter
  2. 2026-01-26-1449-export-adapter

  (Pick a number)
  ```

- **If no specs match**: Use question with the full list:
  ```
  Which spec would you like to fix?

  1. 2026-01-25-1100-rentl-repo-scaffolding
  2. 2026-01-25-1200-pydantic-schemas-validation
  3. 2026-01-25-1937-progress-semantics-tracking
  4. 2026-01-26-1223-import-adapter
  5. 2026-01-26-1449-export-adapter
  ... [list all available specs]

  (Pick a number or specify a custom path)
  ```

Let the user select from the list or provide a custom path.

### Step 2: Read Audit and Identify Fix Items

Read `agent-os/specs/{folder-name}/audit.md`.

Parse the "Action Items" section to find items under "Add to Current Spec (Fix Now)".

If no "Fix Now" items exist:

```
No action items marked "Add to Current Spec (Fix Now)" found in audit.md.

Either:
- All items have been addressed (re-run audit-spec to verify)
- All items were deferred or ignored during the audit

Nothing to fix. Run /audit-spec to verify the spec is complete.
```

Exit the command.

If "Fix Now" items exist, present a summary:

```
Found N action items to fix:

1. [Priority: High] {description}
   Location: {file}:{line}

2. [Priority: Medium] {description}
   Location: {file}:{line}

...

I'll address each item in order. Ready to proceed? (yes / abort)
```

### Step 3: Address Each Action Item

For each "Fix Now" item:

1. **Read the cited file and surrounding context**
   - Open the file at the specified line
   - Understand the issue in context

2. **Determine the fix**
   - Based on the action item description and category (Performance, Security, etc.)
   - Reference the standard if a standards violation is cited

3. **Apply the fix**
   - Make the necessary code changes
   - Keep changes minimal and focused on the specific issue

4. **Log progress**
   - After each fix, note what was changed

Continue until all items are addressed.

### Step 4: Run Verification

Run `make all` to ensure all fixes pass quality checks:

```bash
make all
```

If `make all` fails:
- Identify which check failed (format, lint, type, test)
- Fix the issue
- Re-run `make all`
- Repeat until green

### Step 5: Report Results

Summarize the fixes and next steps:

```
Fix complete! Addressed N action items:

✓ [1] {description} — Fixed by {brief explanation}
✓ [2] {description} — Fixed by {brief explanation}
...

Verification: `make all` passed ✓

Next steps:
1. Run /audit-spec to verify all issues are resolved
2. If new issues are found, run /fix-spec again
3. Repeat until audit shows all 5/5 scores with no action items
```

If any items could not be addressed:

```
Fix partially complete. Addressed M of N action items:

✓ [1] {description} — Fixed by {brief explanation}
✗ [2] {description} — Could not fix: {reason}
...

Items that could not be fixed may need manual intervention or re-evaluation during the next audit.

Next steps:
1. Review the items that could not be fixed
2. Run /audit-spec to update the audit with current state
3. Decide whether to defer or manually address remaining items
```

## Tips

- **Focus on the cited location** — The audit provides file:line for a reason. Start there.
- **Read the standard if cited** — Standards violations should reference the specific rule. Read it for guidance.
- **Keep fixes minimal** — Don't refactor beyond what the action item requires.
- **If unsure, ask** — If an action item is ambiguous, use question to clarify before making changes.
- **Trust the audit** — The user already approved these items during audit. Don't second-guess the categorization.

## Integration with Existing Workflow

Position this command in the development lifecycle:

1. **Run AFTER audit-spec identifies issues**
   - `audit.md` should exist with categorized action items
   - "Fix Now" items are ready to be addressed

2. **Run BEFORE re-auditing**
   - Fixes the issues so the next audit can verify them
   - Enables the iterative improvement loop

3. **Enables the full workflow**
   ```
   shape-spec → audit-spec → fix-spec → audit-spec → (repeat) → all green
   ```

## Workflow Summary

1. User runs fix-spec
2. AI identifies spec and reads audit.md
3. AI finds all "Add to Current Spec (Fix Now)" items
4. AI addresses each item at the cited file:line
5. AI runs `make all` to verify fixes
6. AI reports results and suggests re-running audit-spec

**Success criteria:** All "Fix Now" items are addressed and `make all` passes
