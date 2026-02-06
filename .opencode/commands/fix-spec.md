# Fix Spec

This command has been absorbed into `/do-task`.

Run `/do-task` instead — it automatically detects fix items (from audit-task or audit-spec) and addresses them as part of the normal task loop.

## Workflow

```
shape-spec → [orchestrator: do-task ↔ audit-task loop → run-demo → audit-spec] → walk-spec → PR
```
