# Standards: Test Infrastructure Overhaul

## Primary Standards (directly addressed)

1. **mock-execution-boundary** — Mock at the actual execution boundary per test tier; verify mocks are invoked
2. **mandatory-coverage** — Coverage mandatory for all features; tests must exercise actual behavior
3. **test-timing-rules** — Strict timing limits per tier: unit <250ms, integration <5s, quality <30s
4. **three-tier-test-structure** — All tests in unit/integration/quality folders; no exceptions
5. **bdd-for-integration-quality** — Integration and quality tests must use BDD-style (Given/When/Then)

## Adjacent Standards (must not violate)

6. **make-all-gate** — Gate tiers: make check (task), make ci (CI PR), make all (spec)
7. **no-test-skipping** — Never skip tests within a tier
8. **no-mocks-for-quality-tests** — Quality tests use real LLMs; integration tests mock LLMs
