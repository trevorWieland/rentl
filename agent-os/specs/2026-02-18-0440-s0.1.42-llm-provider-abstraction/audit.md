status: fail
fix_now_count: 1

# Audit: s0.1.42 LLM Provider Abstraction & Agent Wiring

- Spec: s0.1.42
- Issue: https://github.com/trevorWieland/rentl/issues/129
- Date: 2026-02-18
- Round: 2

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 4/5
- Completion: 4/5
- Security: 5/5
- Stability: 5/5

## Non-Negotiable Compliance
1. No direct provider/model instantiation outside the factory: **FAIL** — Direct instantiation remains outside the factory in `tests/quality/agents/quality_harness.py:96`, `tests/quality/agents/quality_harness.py:98`, `tests/quality/agents/quality_harness.py:102` (`OpenRouterProvider`, `OpenAIProvider`, `OpenAIChatModel`), violating the single-factory requirement. Centralized instantiation remains in `packages/rentl-llm/src/rentl_llm/provider_factory.py:419`, `packages/rentl-llm/src/rentl_llm/provider_factory.py:420`, `packages/rentl-llm/src/rentl_llm/provider_factory.py:459`, `packages/rentl-llm/src/rentl_llm/provider_factory.py:460`.
2. Model ID validation at the config boundary: **PASS** — Regex `^[^/]+/.+` is declared in schema config `packages/rentl-schemas/src/rentl_schemas/config.py:25` and enforced in `RunConfig` parse-time validator `packages/rentl-schemas/src/rentl_schemas/config.py:699`; invalid OpenRouter IDs are rejected during config validation (`packages/rentl-schemas/src/rentl_schemas/config.py:717`) with tests in `tests/unit/schemas/test_config.py:608` and `tests/unit/schemas/test_config.py:664`.
3. Tools registered as `pydantic_ai.Tool` objects with explicit names: **PASS** — Tool wrapping with explicit `name`/`description` is implemented in `packages/rentl-agents/src/rentl_agents/factory.py:297` and `packages/rentl-agents/src/rentl_agents/tools/registry.py:168`; harness accepts `list[Tool]` in `packages/rentl-agents/src/rentl_agents/harness.py:90`; unit tests verify named Tool output in `tests/unit/rentl-agents/test_factory.py:342`.
4. No test deletions or modifications to make audits pass: **PASS** — Demo evidence shows full verification gate passing with expanded test coverage (`make all` includes 910 unit, 95 integration, 9 quality) in `agent-os/specs/2026-02-18-0440-s0.1.42-llm-provider-abstraction/demo.md:313`; new spec-specific tests are present in `tests/unit/llm/test_provider_factory.py:29` and `tests/integration/byok/test_local_model_factory.py:160`.

## Demo Status
- Latest run: PASS (Run 29, 2026-02-18)
- Run 29 passes all 7 demo steps, including OpenRouter/local routing validation and full verification gate (`agent-os/specs/2026-02-18-0440-s0.1.42-llm-provider-abstraction/demo.md:306`, `agent-os/specs/2026-02-18-0440-s0.1.42-llm-provider-abstraction/demo.md:314`).

## Standards Adherence
- `openrouter-provider-routing`: PASS — Provider-qualified model ID validation at config parse (`packages/rentl-schemas/src/rentl_schemas/config.py:699`), `require_parameters` enforcement in preflight (`packages/rentl-llm/src/rentl_llm/provider_factory.py:381`), probe-before-run checks (`packages/rentl-llm/src/rentl_llm/provider_factory.py:221`), and allowlist enforcement (`packages/rentl-llm/src/rentl_llm/provider_factory.py:124`).
- `adapter-interface-protocol`: PASS — LLM and HTTP boundaries are injected/abstracted for this scope (`packages/rentl-llm/src/rentl_llm/openai_runtime.py:31`, `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:21`).
- `agent-tool-registration`: PASS — Agents receive explicit `Tool` objects, not raw callables (`packages/rentl-agents/src/rentl_agents/tools/registry.py:168`, `packages/rentl-agents/src/rentl_agents/runtime.py:477`).
- `pydantic-ai-structured-output`: PASS — Structured calls use `Agent(..., output_type=..., output_retries=...)` (`packages/rentl-llm/src/rentl_llm/openai_runtime.py:47`, `packages/rentl-agents/src/rentl_agents/harness.py:253`, `packages/rentl-core/src/rentl_core/benchmark/judge.py:171`).
- `batch-alignment-feedback`: PASS — Alignment checks handle missing/extra/duplicate IDs with structured retry feedback (`packages/rentl-agents/src/rentl_agents/wiring.py:116`, `packages/rentl-agents/src/rentl_agents/wiring.py:141`), with tests for extra/missing/both (`tests/unit/rentl-agents/test_alignment_retries.py:286`, `tests/unit/rentl-agents/test_alignment_retries.py:328`, `tests/unit/rentl-agents/test_alignment_retries.py:373`).
- `strict-typing-enforcement`: PASS — Spec-introduced files avoid `Any`/`object` usage in implementation and corrected integration test typing (`tests/integration/byok/test_local_model_factory.py:45`, `tests/integration/byok/test_local_model_factory.py:78`).
- `pydantic-only-schemas`: PASS — New schemas in scope use Pydantic/BaseSchema with `Field` metadata (`packages/rentl-llm/src/rentl_llm/provider_factory.py:151`, `packages/rentl-llm/src/rentl_llm/provider_factory.py:192`).
- `mock-execution-boundary`: PASS — Unit tests patch execution boundaries and assert invocation (e.g., `_probe_endpoint`, `create_model`, `Agent.run`) in `tests/unit/llm/test_provider_factory.py:289`, `tests/unit/llm/test_provider_factory.py:307`, `tests/unit/llm/test_provider_factory.py:637`.

## Regression Check
- Prior failures in Task 2/3/6/9/10 and Demo runs 1-27 remain resolved (`agent-os/specs/2026-02-18-0440-s0.1.42-llm-provider-abstraction/audit-log.md:9`, `agent-os/specs/2026-02-18-0440-s0.1.42-llm-provider-abstraction/audit-log.md:11`, `agent-os/specs/2026-02-18-0440-s0.1.42-llm-provider-abstraction/audit-log.md:15`, `agent-os/specs/2026-02-18-0440-s0.1.42-llm-provider-abstraction/audit-log.md:46`).
- New compliance regression against spec non-negotiable #1: a remaining direct model/provider construction path persists in quality harness utilities (`tests/quality/agents/quality_harness.py:96`, `tests/quality/agents/quality_harness.py:98`, `tests/quality/agents/quality_harness.py:102`).

## Action Items

### Fix Now
- Route quality harness judge model construction through `create_model()` and remove direct `OpenRouterProvider`/`OpenAIProvider`/`OpenAIChatModel` instantiation (`tests/quality/agents/quality_harness.py:96`, `tests/quality/agents/quality_harness.py:98`, `tests/quality/agents/quality_harness.py:102`).

### Deferred
- None.
