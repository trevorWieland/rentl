# Standards: Project Bootstrap Command

## Applied Standards

### Architecture
- **api-response-format** — Init output follows the `{data, error, meta}` envelope pattern
- **thin-adapter-pattern** — CLI `init` command is a thin adapter; all business logic (config generation, file creation) lives in `rentl-core`
- **naming-conventions** — Generated files and code follow project naming conventions (snake_case modules/functions, PascalCase classes)

### Python
- **modern-python-314** — Use Python 3.14 features throughout
- **pydantic-only-schemas** — `InitAnswers` and `InitResult` use Pydantic with `Field` and validators
- **strict-typing-enforcement** — No `Any` or `object` types; all fields fully typed with descriptions

### Testing
- **three-tier-test-structure** — Unit tests for core logic, integration tests for end-to-end init flow
- **mandatory-coverage** — All new code covered by tests
- **make-all-gate** — Full verification gate must pass

### UX
- **frictionless-by-default** — Guided setup with sensible defaults; press Enter through for a working project
- **trust-through-transparency** — Clear output showing what was created and what to do next
- **progress-is-product** — Summary panel shows created files and next steps immediately
