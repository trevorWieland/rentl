# Contributing

Thanks for helping build rentl. This repo uses a custom-tailored version of Agent OS and a spec-driven workflow.

## Quick Start (Local Setup)

Requirements:
- Python >= 3.14
- `uv`
- `gh` (GitHub CLI)

Setup:

```bash
make install
```

Run the full verification gate:

```bash
make all
```

## Agent OS Workflow (Spec-Driven)

We use custom commands in:
- `.opencode/commands/`
- `.claude/commands/agent-os/`

Core workflow:

```
shape-spec → do-spec → audit-spec → fix-spec → (repeat) → walk-spec → PR
```

Highlights:
- **shape-spec**: resolves or creates a GitHub spec issue, creates the branch, interviews, writes the plan/spec docs, and commits spec docs only.
- **do-spec**: implements Tasks 2..N from the plan and runs `make all`.
- **audit-spec / fix-spec**: iteratively audit and address issues.
- **walk-spec**: manual validation and PR submission.

## GitHub Issues, Spec IDs, and Roadmap Sync

GitHub is the source of truth for spec IDs.

When creating a new spec:
- Check GitHub for the next available `spec_id` in the target version.
- Use labels: `type:spec`, `status:planned`, `version:vX.Y`.

To align local roadmap with GitHub:
- Run `/sync-roadmap`.

## Branching and PRs

- Use the issue branch created by `shape-spec` (via `gh issue develop`).
- Keep spec docs committed before implementation changes.
- `walk-spec` ends by submitting a PR.

## Testing and Quality Gates

Run the full gate before finishing any spec:

```bash
make all
```

Key targets:
- `make format`
- `make lint`
- `make type`
- `make unit`
- `make integration`
- `make quality`

## Questions

If you are unsure about the workflow or where to start, open an issue and tag it with `type:spec` or ask in an existing spec issue thread.
