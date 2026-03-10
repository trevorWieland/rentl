# Standards: Benchmark Harness v0.1

## Applicable Standards

- **testing/three-tier-test-structure** — Benchmark tests in quality tier (real LLM calls), supporting tests in unit/integration
- **testing/no-mocks-for-quality-tests** — Quality benchmark test uses real LLMs, no mocks
- **testing/bdd-for-integration-quality** — BDD-style structure for benchmark test scenarios
- **python/pydantic-only-schemas** — All benchmark data models (report, rubric, scores) use Pydantic
- **python/async-first-design** — Async for parallel benchmark evaluation (download, translate, judge)
- **python/strict-typing-enforcement** — No Any types in benchmark schemas; all fields use Field with description
- **ux/trust-through-transparency** — Clear reporting of scores, reasoning, and comparisons
- **testing/validate-generated-artifacts** — Benchmark outputs validate against Pydantic schemas
