# Do Spec

This command has been replaced by `/do-task` in the v2 workflow.

`/do-task` implements one task per invocation (instead of all tasks in one session), enabling per-task auditing and automated orchestration.

Run `/do-task` for individual task implementation, or use the orchestrator script for the full automated loop.

## Workflow

```
shape-spec → [orchestrator: do-task ↔ audit-task loop → run-demo → audit-spec] → walk-spec → PR
```
