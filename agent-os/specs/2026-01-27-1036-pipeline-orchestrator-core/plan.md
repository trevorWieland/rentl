# Pipeline Orchestrator Core Plan

## Goal
- Rework the orchestration core to align with spec 07 and the v0.1 roadmap while biasing decisions toward v0.2+ multi-agent readiness.
- Enforce dependency gating, deterministic merges, and staleness tracking with clear lifecycle events and progress updates.
- Define artifact persistence rules so downstream specs (08, 09, 10, 11, 24, 27, 28) can build on reliable run state.

## Execution Note
- Execute Task 1 now, then continue with implementation tasks.

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals.

## Task 2: Define the updated orchestration contract
- Specify hard vs soft dependencies per phase (ingest/context/pretranslation/translate/QA/edit/export).
- Define blocked vs failed behaviors and the event/progress signals for each.
- Codify multi-language invariants (per-language phase independence, shared context).
- Define v0.2-ready execution/sharding expectations (agent fan-out, chunk/scene strategies).

## Task 3: Artifact persistence policy + lineage
- Define which phase outputs must always be persisted vs optional.
- Specify how artifacts are referenced in run state and phase run history.
- Align persistence events with the log/event taxonomy and storage protocols.

## Task 4: Run/phase lifecycle emissions + progress semantics
- Align run/phase events with the event taxonomy (started/completed/failed/blocked/invalidated).
- Emit run-level progress events (run_started/run_completed/run_failed) in addition to phase events.
- Ensure progress summaries remain valid across reruns and out-of-order phase execution.

## Task 5: Orchestrator implementation updates
- Update `PipelineOrchestrator` to enforce gating rules and emit blocked events.
- Track dependency lineage and mark stale outputs on upstream reruns.
- Preserve deterministic merges and ordering with multi-agent readiness.
- Apply the artifact persistence policy in phase execution.

## Task 6: Tests (unit)
- Cover dependency gating (blocked vs failed) and multi-language target handling.
- Validate staleness invalidation and lineage recording.
- Validate artifact persistence rules and log/progress emissions.

## Task 7: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass.
- Fix failures and re-run until green.

## References Studied
- `packages/rentl-core/src/rentl_core/orchestrator.py`
- `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
- `packages/rentl-core/src/rentl_core/ports/storage.py`
- `packages/rentl-schemas/src/rentl_schemas/config.py`
- `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- `packages/rentl-schemas/src/rentl_schemas/progress.py`
- `packages/rentl-schemas/src/rentl_schemas/events.py`
- `agent-os/specs/2026-01-25-1937-progress-semantics-tracking/plan.md`
- `agent-os/specs/2026-01-26-1835-run-persistence-artifact-store/plan.md`
- `agent-os/specs/2026-01-26-2206-log-event-taxonomy-sinks/plan.md`

## Standards Applied
- architecture/adapter-interface-protocol
- architecture/log-line-format
- architecture/naming-conventions
- architecture/none-vs-empty
- architecture/thin-adapter-pattern
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- testing/make-all-gate
- ux/progress-is-product
- ux/speed-with-guardrails
- ux/trust-through-transparency

## Product Alignment
- v0.1 demands a deterministic phase-based pipeline with transparent progress and auditable outputs.
- This spec biases toward v0.2+ multi-agent orchestration while keeping v0.1 runnable and reliable.
