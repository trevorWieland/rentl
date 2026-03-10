# Progress Semantics & Tracking Plan

## Goal
- Define a trustworthy, phase-aware progress model for the v0.1 pipeline
- Ensure progress reporting is monotonic, explainable, and aligned with phase/line/scene observability
- Extend schemas and validation so progress can be emitted consistently in logs and CLI/API responses

## Execution Note
- Execute Task 1 now, then continue with implementation tasks

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals

## Task 2: Define progress semantics and invariants
- Establish a phase-by-phase progress model (context, pretranslation, translate, QA, edit) with explicit unit types (lines/scenes/characters/issues/edits)
- Define monotonic progress rules (no decreasing %), including handling of unknown totals via discovery/locked totals and "lower-bound" vs "estimated" reporting
- Specify completion criteria and sub-metrics per phase (e.g., context: scene coverage + character bios completeness; QA: lines checked + issues resolved)
- Define how overall run progress is computed (phase weights + criteria) and when a percent is valid vs omitted

## Task 3: Extend progress schemas in `rentl-schemas`
- Add progress enums/types (unit types, metric keys, progress mode/status) in `packages/rentl-schemas/src/rentl_schemas/primitives.py` or a new `progress.py`
- Replace/expand `PhaseProgress` + `RunProgress` to support multiple metrics, optional totals, percent validity flags, and ETA fields in `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- Update `packages/rentl-schemas/src/rentl_schemas/__init__.py` exports and keep Field descriptions/validators strict

## Task 4: Define progress reporting payloads
- Add a typed `ProgressSnapshot`/`ProgressUpdate` model for CLI/API responses (enveloped per `architecture/api-response-format`)
- Add progress event data shapes for JSONL logs and align event naming with `architecture/log-line-format`

## Task 5: Validation helpers and tests
- Add validation helpers in `packages/rentl-schemas/src/rentl_schemas/validation.py` for progress invariants (monotonic %, totals non-negative, None vs empty lists)
- Add unit tests covering phase metrics, overall aggregation, and boundary cases (unknown totals, discovery -> locked)

## Task 6: Document integration touchpoints
- Note where orchestrator/agents will emit progress updates (phase start/milestone/complete) and how they map to the new schema

## References Studied
- `agent-os/specs/2026-01-25-1200-pydantic-schemas-validation/`
- Existing schemas in `packages/rentl-schemas/src/rentl_schemas/`

## Standards Applied
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- architecture/log-line-format
- architecture/api-response-format
- architecture/naming-conventions
- architecture/none-vs-empty
- ux/progress-is-product
- ux/trust-through-transparency
- ux/speed-with-guardrails

## Product Alignment
- v0.1 scope includes progress observability by phase/line/scene
