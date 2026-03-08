# Standards: CLI Exit Codes + Error Taxonomy

## Applicable Standards

### Architecture

- **api-response-format** — Error responses use the {data, error, meta} envelope; exit_code field added to error section
- **thin-adapter-pattern** — CLI is a thin adapter; exit code mapping lives at the CLI surface, domain errors stay in core
- **naming-conventions** — snake_case for error code identifiers, UPPER_SNAKE for enum members

### Python

- **pydantic-only-schemas** — ExitCode enum and ErrorResponse use Pydantic-compatible types
- **strict-typing-enforcement** — No Any types in error taxonomy; all mappings fully typed

### Testing

- **bdd-for-integration-quality** — Integration tests for exit codes use BDD (Given/When/Then)
- **three-tier-test-structure** — Unit tests for enum/mapping, integration tests for CLI exit code behavior
- **mandatory-coverage** — All exit code paths covered by tests

### UX

- **trust-through-transparency** — Exit codes are stable, documented, and predictable
- **progress-is-product** — Error codes visible in both interactive and JSON output
