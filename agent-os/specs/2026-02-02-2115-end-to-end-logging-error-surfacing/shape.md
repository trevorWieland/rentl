# End-to-End Logging & Error Surfacing — Shaping Notes

## Scope

Implement milestone 25b: full logging coverage with actionable error surfacing. Logging must work for pipeline runs and individual commands, support multiple sink types (console, file, no-op), and avoid silent failures. Backward compatibility should be minimized by making log sink configuration mandatory.

## Decisions

- Log sink configuration is mandatory; no implicit defaults.
- Provide explicit sink types: console, file (storage-backed), and no-op.
- Add command-level logging events for CLI commands.
- Avoid lazy imports and prevent circular dependencies when wiring sinks.
- Preserve strict typing and Pydantic-only schemas for all logging config and events.

## Context

- **Visuals:** None
- **References:** Scattered logging/progress usage and existing exception types across core/cli/storage; see references.md for locations.
- **Product alignment:** Observability and progress tracking are core; JSONL logs and standardized event schemas are required. API keys must never be logged. CLI is primary surface; reliability and auditability are critical.

## Standards Applied

- testing/make-all-gate — Verification required before completion
- architecture/log-line-format — JSONL log entries with stable schema
- ux/trust-through-transparency — no silent failures; actionable errors
- ux/progress-is-product — progress status must be visible
- architecture/api-response-format — CLI responses keep {data, error, meta} envelopes
- python/strict-typing-enforcement — no Any/object; Field descriptions required
- python/pydantic-only-schemas — schemas must be Pydantic
- global/address-deprecations-immediately — fix deprecations now
