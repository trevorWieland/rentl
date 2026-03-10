# Standards: Sample Project + Golden Artifacts

## Applicable Standards

### Testing
- **validate-generated-artifacts** — Golden artifacts must validate against consuming component schemas, not just syntax
- **three-tier-test-structure** — Schema validation tests in unit/, ingest and pipeline tests in integration/
- **bdd-for-integration-quality** — Integration tests use BDD-style Given/When/Then
- **mandatory-coverage** — Tests must exercise actual behavior, not just existence
- **test-timing-rules** — Unit <250ms, integration <5s
- **no-test-skipping** — All new tests must run and pass
- **make-all-gate** — `make all` must pass before finalizing

### Architecture
- **log-line-format** — Any sample config/logs follow the standard JSONL format
- **naming-conventions** — File and module naming follow snake_case conventions

### Python
- **pydantic-only-schemas** — Golden artifacts use Pydantic models from rentl-schemas
- **strict-typing-enforcement** — No Any types in new code

### UX
- **frictionless-by-default** — Sample project is discoverable and works with default config
