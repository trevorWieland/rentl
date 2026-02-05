---
description: Sync roadmap.md with GitHub spec issues and resolve conflicts.
---

# Sync Roadmap

Align `agent-os/product/roadmap.md` with GitHub issues labeled `type:spec`. Use GitHub as the source of truth for spec ids.

## Important Guidelines

- **Always use question tool** when asking the user anything
- **Prefer GitHub issues** for spec id allocation and dependency relationships
- **Ask on conflicts** — never overwrite silently

## Process

### Step 1: Load Sources

1. Read `agent-os/product/roadmap.md` and parse spec items:
   - `spec_id`, title, description, depends_on, status (✅ or planned), version
2. Fetch GitHub issues with label `type:spec`:
   - title, body frontmatter (`spec_id`, `version`, `status`, `depends_on`), labels, milestone, relationships

### Step 2: Compare and Classify

For each `spec_id`, determine:
- **Match**: present in both sources
- **Roadmap-only**: missing in GitHub
- **GitHub-only**: missing in roadmap
- **Conflict**: fields differ (title, status, version, depends_on)

### Step 3: Resolve Conflicts (Ask)

For each conflict, use question with a recommended default:

```
Conflict for sX.Y.ZZ:
- Roadmap: <title/status/version/depends>
- GitHub: <title/status/version/depends>

Which should we keep?
1. GitHub (Recommended)
2. Roadmap
```

Apply the user’s choice per conflict.

### Step 4: Apply Sync Actions

**If Roadmap-only:**
- Create a GitHub issue using the roadmap data.
- Before creation, verify `spec_id` isn’t already used on GitHub.

**If GitHub-only:**
- Add a roadmap entry under the correct version section.

**If Match:**
- Ensure dependencies are aligned with GitHub relationships.

### Step 5: Dependency Alignment

- If GitHub has blocked-by relationships, update `depends_on` in roadmap.
- If roadmap has dependencies missing in GitHub, add blocked-by relationships.

### Step 6: Report Summary

Summarize:
- Issues created
- Roadmap entries added
- Conflicts resolved
- Dependencies updated

## Notes

- When creating new spec issues elsewhere, always check GitHub for the next available `spec_id` in the target version.
