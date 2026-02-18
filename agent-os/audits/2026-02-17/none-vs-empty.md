---
standard: none-vs-empty
category: architecture
score: 100
importance: High
violations_count: 0
date: 2026-02-17
status: clean
---

# Standards Audit: None vs Empty Lists

**Standard:** `architecture/none-vs-empty`
**Date:** 2026-02-17
**Score:** 100/100
**Importance:** High

## Summary

The codebase consistently applies the `None` vs `[]` contract in schema definitions and phase outputs. Optional list fields are typed to allow `None` and initialized with `Field(None)` (or equivalent), while required output list fields are always populated with a list and return `[]` when no items exist. No direct violations of the standard were found across the audited files, including schema modules, phase outputs, and orchestration/agent wiring paths.

## Violations

No violations found.

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/phases.py:213` — `ContextPhaseInput.glossary` is optional (`list[GlossaryTerm] | None`) with `Field(None, description=...)`.
- `packages/rentl-schemas/src/rentl_schemas/phases.py:307` — `PretranslationPhaseInput.glossary` remains optional and defaults to `None` rather than an empty list.
- `packages/rentl-schemas/src/rentl_schemas/config.py:158` — routing-related list field is optional and explicitly initialized to `None`.
- `packages/rentl-core/src/rentl_core/orchestrator.py:2268` — required context output fields are instantiated from merged context values as list objects, not `None`.
- `packages/rentl-agents/src/rentl_agents/wiring.py:237` — context agent returns required `context_notes` as `[]` when no notes are present.
- `packages/rentl-agents/src/rentl_agents/qa/lines.py:269` — required `issues` output field is returned as `[]` in empty-case handling.

## Scoring Rationale

- **Coverage:** 100% of the relevant schema/list-production paths inspected follow the standard (all optional list fields use `None` defaults, and all required output lists are constructed as lists and emit `[]` when empty).
- **Severity:** No violations were found, so severity is effectively zero.
- **Trend:** Consistent pattern is observed across older and newer modules in schema, core orchestration, and agents layers.
- **Risk:** Practical risk from this standard is currently low because semantics are consistently implemented and should not introduce `None`/empty-list ambiguity in serialized phase contracts.
