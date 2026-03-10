# References for Quality Test Suite

## Similar Implementations

### Integration: Direct Translator Profile

- **Location:** `tests/integration/agents/test_direct_translator.py`
- **Relevance:** BDD-style integration tests for agent profile loading and wiring
- **Key patterns:** pytest-bdd Given/When/Then structure; profile validation checks

### Integration: BYOK Runtime

- **Location:** `tests/integration/byok/test_openai_runtime.py`
- **Relevance:** Config-driven runtime tests using env vars and schema validation
- **Key patterns:** TOML config setup, env-driven API keys, validation plans

### Integration: Deterministic QA

- **Location:** `tests/integration/core/test_deterministic_qa.py`
- **Relevance:** End-to-end QA flow validation with runtime configuration
- **Key patterns:** Integration marker usage, configured runner checks

### Agent Runtime Implementation

- **Location:** `packages/rentl-agents/src/rentl_agents/runtime.py`
- **Relevance:** Structured output, tool registration, retries, output modes
- **Key patterns:** Tool callables, output mode selection, retry limits
