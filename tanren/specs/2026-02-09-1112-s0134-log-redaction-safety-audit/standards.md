# Standards: Log Redaction & Safety Audit

## Applied Standards

1. **architecture/log-line-format** — Redaction must preserve the JSONL schema ({timestamp, level, event, run_id, phase, message, data}). Redacted values replace in-place; no fields are removed.

2. **python/strict-typing-enforcement** — RedactionConfig, SecretPattern, and Redactor use typed Pydantic fields with Field descriptions. No `Any` or `object` types.

3. **python/pydantic-only-schemas** — All new schemas (RedactionConfig, SecretPattern) use Pydantic BaseSchema, not dataclasses.

4. **ux/trust-through-transparency** — Redaction is visible: a debug-level log entry records when redaction occurred. No silent masking without trace.

5. **architecture/adapter-interface-protocol** — Redaction logic lives in the schemas/core layer. Log sinks access it via composition, not by modifying the LogSinkProtocol.

6. **testing/make-all-gate** — All code must pass `make all` (format, lint, type, unit, integration).

7. **testing/mandatory-coverage** — Redaction patterns, dict traversal, sink integration, and config scanning all require test coverage.

8. **testing/three-tier-test-structure** — Unit tests for pattern matching and dict traversal. Integration tests for sink pipeline and artifact storage redaction.
