# Progress Semantics & Tracking - Shaping Notes

## Scope
- Build a thorough progress model for all five phases with phase-specific units
- Ensure progress reporting is monotonic and trustworthy (no decreasing percent)
- Make progress interpretable for both external and internal stakeholders

## Decisions
- Model progress per phase with explicit units and sub-metrics
- Support unknown totals via discovery, then lock totals before reporting percent
- Only report percentages when totals are known and monotonic

## Context
- Visuals: None
- References: Schema definitions spec and current schema files
- Product alignment: v0.1 progress observability by phase/line/scene

## Standards Applied
- python/pydantic-only-schemas - schemas are Pydantic models
- python/strict-typing-enforcement - no Any/object; Field descriptions required
- architecture/log-line-format - progress events emit JSONL log lines
- architecture/api-response-format - progress data returned via envelope
- architecture/naming-conventions - consistent naming across models and fields
- architecture/none-vs-empty - distinguish unknown vs empty metric lists
- ux/progress-is-product - progress visibility is core
- ux/trust-through-transparency - explainable progress states and errors
- ux/speed-with-guardrails - deterministic updates with quality guardrails
