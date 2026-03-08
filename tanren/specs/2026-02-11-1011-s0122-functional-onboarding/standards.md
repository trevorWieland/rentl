# Standards: Functional Onboarding

## Applicable Standards

### UX
- **ux/frictionless-by-default** — Guided setup and safe defaults for effortless first runs
- **ux/trust-through-transparency** — No silent stalls; every phase, error, and status must be visible and explainable
- **ux/progress-is-product** — Status, phase completion, and QA visibility must be immediate and unambiguous

### Architecture
- **architecture/thin-adapter-pattern** — Surface layers (CLI) are thin adapters; all business logic lives in Core Domain
- **architecture/config-path-resolution** — Config paths resolve relative to config file parent, not CWD
- **architecture/api-response-format** — All responses use pydantic-based {data, error, meta} envelopes
- **architecture/openrouter-provider-routing** — Validate OpenRouter provider compatibility before pipeline runs

### Testing
- **testing/validate-generated-artifacts** — Generated artifacts must validate against consuming component schemas
- **testing/bdd-for-integration-quality** — Integration and quality tests must use BDD-style (Given/When/Then)
- **testing/mandatory-coverage** — Coverage mandatory for all features; tests must exercise actual behavior
- **testing/make-all-gate** — Require `make all` to pass before finalizing work

### Global
- **global/no-placeholder-artifacts** — Never commit placeholder values; all artifacts must be functional and verified
