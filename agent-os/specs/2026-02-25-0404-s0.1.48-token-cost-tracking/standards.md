# Standards: Comprehensive Token & Cost Tracking

## Applied Standards

### Architecture
- **log-line-format** — Cost/token telemetry must use the stable JSONL log schema with {timestamp, level, event, run_id, phase, message, data} fields
- **api-response-format** — Status output uses pydantic-based {data, error, meta} envelopes
- **thin-adapter-pattern** — Cost aggregation logic lives in rentl-core (`cost.py`), CLI just displays results

### Python
- **pydantic-only-schemas** — New cost/token models use Pydantic with Field and validators (no dataclasses)
- **strict-typing-enforcement** — No `Any` or `object` types in cost schemas; all fields have explicit types
- **async-first-design** — Cost-related APIs follow async patterns if involving network calls

### Testing
- **three-tier-test-structure** — Unit tests in `unit/`, integration tests in `integration/`
- **mandatory-coverage** — Coverage required for all new cost/token code
- **mock-execution-boundary** — Mock at LLM boundary for cost unit tests; mock pydantic-ai responses
- **bdd-for-integration-quality** — Integration tests use Given/When/Then BDD style
- **test-timing-rules** — Unit tests <250ms each, integration tests <5s each

### Global
- **no-placeholder-artifacts** — No stub cost modules; all code must be functional at commit time
