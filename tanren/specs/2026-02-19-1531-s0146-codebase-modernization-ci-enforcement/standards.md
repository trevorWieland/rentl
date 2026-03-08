# Standards: Codebase Modernization & CI Enforcement

## Applicable Standards

### Python
- **pydantic-only-schemas** — Never use dataclasses or plain classes; all schemas must use Pydantic with Field and validators
- **modern-python-314** — Use Python 3.14 modern features; avoid legacy constructs and outdated patterns
- **strict-typing-enforcement** — Never use Any or object in types; all Pydantic fields use Field with description and built-in validators

### Testing
- **make-all-gate** — Require `make all` to pass before finalizing work

### Global
- **address-deprecations-immediately** — Deprecation warnings must be addressed immediately; never defer to future work
- **no-placeholder-artifacts** — Never commit placeholder values; all artifacts must be functional and verified at commit time
- **prefer-dependency-updates** — Prefer frequent dependency updates; use compatible ranges instead of exact pins

### Architecture
- **id-formats** — UUIDv7 vs human-readable ID formats
- **api-response-format** — All responses use pydantic-based {data, error, meta} envelopes
