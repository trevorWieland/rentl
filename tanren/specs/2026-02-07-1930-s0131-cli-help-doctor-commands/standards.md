# Standards: CLI Help/Doctor Commands

## Applicable Standards

### Architecture
- **thin-adapter-pattern** — CLI commands are thin adapters; all diagnostic logic lives in rentl-core
- **naming-conventions** — Consistent naming across new modules (snake_case functions, PascalCase models)

### Python
- **async-first-design** — Doctor checks may need async (e.g., LLM connectivity validation)
- **strict-typing-enforcement** — No Any/object in new types; all Pydantic fields use Field with description
- **pydantic-only-schemas** — All new schemas (CheckResult, DoctorReport, PhaseInfo, CommandInfo) use Pydantic

### Testing
- **three-tier-test-structure** — Unit tests for core modules, integration tests for CLI commands
- **mandatory-coverage** — All new code must have test coverage
- **make-all-gate** — Must pass `make all` before finalizing

### UX
- **frictionless-by-default** — Commands work without config where possible; doctor handles missing config gracefully
- **trust-through-transparency** — Doctor output explains what's wrong and how to fix it
- **progress-is-product** — Status visibility in doctor output (clear pass/fail/warn indicators)
