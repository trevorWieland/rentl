# Standards Audit Triage — 2026-02-17

## Score Distribution

| Standard | Category | Score | Importance | Priority | Status |
|----------|----------|-------|------------|----------|--------|
| `openrouter-provider-routing` | architecture | 42 | High | 174 | violations-found |
| `copy-pasteable-examples` | ux | 43 | High | 171 | violations-found |
| `speed-with-guardrails` | ux | 44 | High | 168 | violations-found |
| `mock-execution-boundary` | testing | 44 | High | 168 | violations-found |
| `frictionless-by-default` | ux | 58 | High | 126 | violations-found |
| `mandatory-coverage` | testing | 58 | High | 126 | violations-found |
| `test-timing-rules` | testing | 62 | High | 114 | violations-found |
| `thin-adapter-pattern` | architecture | 62 | High | 114 | violations-found |
| `validate-generated-artifacts` | testing | 62 | High | 114 | violations-found |
| `agent-tool-registration` | global | 72 | High | 84 | violations-found |
| `config-path-resolution` | architecture | 72 | High | 84 | violations-found |
| `batch-alignment-feedback` | global | 74 | High | 78 | violations-found |
| `pydantic-ai-structured-output` | global | 76 | High | 72 | violations-found |
| `pydantic-only-schemas` | python | 76 | High | 72 | violations-found |
| `stale-reference-prevention` | ux | 76 | High | 72 | violations-found |
| `naming-conventions` | architecture | 76 | Medium | 48 | violations-found |
| `async-first-design` | python | 78 | High | 66 | violations-found |
| `make-all-gate` | testing | 78 | High | 66 | violations-found |
| `bdd-for-integration-quality` | testing | 79 | High | 63 | violations-found |
| `adapter-interface-protocol` | architecture | 82 | High | 54 | violations-found |
| `trust-through-transparency` | ux | 82 | High | 54 | violations-found |
| `progress-is-product` | ux | 82 | Medium | 36 | violations-found |
| `address-deprecations-immediately` | global | 84 | High | 48 | violations-found |
| `three-tier-test-structure` | testing | 84 | High | 48 | violations-found |
| `strict-typing-enforcement` | python | 87 | High | 39 | violations-found |
| `id-formats` | architecture | 87 | High | 39 | violations-found |
| `prefer-dependency-updates` | global | 88 | High | 36 | violations-found |
| `api-response-format` | architecture | 92 | High | 24 | violations-found |
| `no-placeholder-artifacts` | global | 91 | Medium | 18 | violations-found |
| `cli-help-docstring-gating` | python | 72 | Medium | 56 | violations-found |
| `modern-python-314` | python | 72 | Medium | 56 | violations-found |
| `llm-output-tolerance` | python | 100 | High | 0 | clean |
| `log-line-format` | architecture | 100 | High | 0 | clean |
| `no-mocks-for-quality-tests` | testing | 100 | High | 0 | clean |
| `no-test-skipping` | testing | 100 | High | 0 | clean |
| `none-vs-empty` | architecture | 100 | High | 0 | clean |
| `required-tool-gating` | global | 100 | High | 0 | clean |

**Average score:** 75/100
**Clean standards:** 6/37
**Standards with violations:** 31/37

## Issues Created

| # | Title | Standards | Scope | Priority |
|---|-------|-----------|-------|----------|
| #129 | s0.1.42 LLM Provider Abstraction & Agent Wiring | openrouter-provider-routing, adapter-interface-protocol, agent-tool-registration, pydantic-ai-structured-output, batch-alignment-feedback | ~10 files, 13 violations | Critical |
| #130 | s0.1.43 Documentation Placeholders, CLI Surface & UX Polish | copy-pasteable-examples, stale-reference-prevention, frictionless-by-default, thin-adapter-pattern, cli-help-docstring-gating, trust-through-transparency, progress-is-product | ~25 files, ~80 violations | High |
| #131 | s0.1.44 Pipeline Validation, Async Correctness & Config Paths | speed-with-guardrails, validate-generated-artifacts, async-first-design, config-path-resolution | ~14 files, 17 violations | High |
| #132 | s0.1.45 Test Infrastructure Overhaul | mock-execution-boundary, mandatory-coverage, test-timing-rules, three-tier-test-structure, bdd-for-integration-quality | ~18 files, 36 violations | High |
| #133 | s0.1.46 Codebase Modernization & CI Enforcement | pydantic-only-schemas, modern-python-314, strict-typing-enforcement, make-all-gate, address-deprecations-immediately, id-formats, api-response-format, no-placeholder-artifacts, prefer-dependency-updates | ~25 files, ~45 violations | Medium |
| #134 | s0.1.47 Recalibrate Naming Conventions Standard | naming-conventions | 1 file | Low |

## Clean Standards (No Action Needed)

- `llm-output-tolerance` (python) — Score: 100
- `log-line-format` (architecture) — Score: 100
- `no-mocks-for-quality-tests` (testing) — Score: 100
- `no-test-skipping` (testing) — Score: 100
- `none-vs-empty` (architecture) — Score: 100
- `required-tool-gating` (global) — Score: 100

## Deferred / Skipped

None — all violations covered by the 6 created issues.
