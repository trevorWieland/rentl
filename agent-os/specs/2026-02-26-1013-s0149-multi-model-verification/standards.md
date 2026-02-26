# Standards: Multi-Model Verification & Compatibility

## Applicable Standards

1. **openrouter-provider-routing** — OpenRouter provider validation, model ID format, and routing config
2. **pydantic-ai-structured-output** — All LLM calls use pydantic-ai Agent with output_type
3. **three-tier-test-structure** — Tests in unit/integration/quality tiers with timing limits
4. **no-mocks-for-quality-tests** — Quality tests use real LLMs
5. **bdd-for-integration-quality** — Integration/quality tests use BDD style (Given/When/Then)
6. **make-all-gate** — Gate tiers: make check (task), make ci (CI PR), make all (spec)
7. **async-first-design** — Async APIs for parallel agent execution and LLM IO
8. **strict-typing-enforcement** — No Any/object types; all Pydantic fields use Field with description
9. **pydantic-only-schemas** — All schemas use Pydantic with Field and validators
10. **copy-pasteable-examples** — CLI command examples must be executable without modification
11. **thin-adapter-pattern** — CLI is thin adapter; all verification logic lives in core
