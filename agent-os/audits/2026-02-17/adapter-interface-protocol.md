---
standard: adapter-interface-protocol
category: architecture
score: 82
importance: High
violations_count: 4
date: 2026-02-17
status: violations-found
---

# Standards Audit: Adapter Interface Protocol

**Standard:** `architecture/adapter-interface-protocol`
**Date:** 2026-02-17
**Score:** 82/100
**Importance:** High

## Summary

Core orchestration and storage paths consistently consume infrastructure through protocol interfaces from `rentl_core.ports`, and the BYOK runtime adapter in `rentl_llm` also follows the protocol contract. However, several production modules still instantiate model/provider/runtime implementations directly (`OpenAI`/`OpenRouter` and `httpx.AsyncClient`) instead of depending on core-defined abstractions, creating tight coupling in critical model execution and benchmark paths. The codebase is mostly compliant, but these boundary leaks are concentrated in model execution and external download paths, which are high-impact locations for maintainability and testability.

## Violations

### Violation 1: Agents build concrete LLM clients and models directly in ProfileAgent

- **File:** `packages/rentl-agents/src/rentl_agents/runtime.py:438`
- **Severity:** High
- **Evidence:**
  ```python
  provider = OpenRouterProvider(api_key=self._config.api_key)
  model = OpenRouterModel(self._config.model_id, provider=provider)
  ...
  provider = OpenAIProvider(base_url=base_url, api_key=self._config.api_key)
  model = OpenAIChatModel(self._config.model_id, provider=provider)
  ```
- **Recommendation:** Inject a runtime protocol (e.g., `LlmRuntimeProtocol`) into `ProfileAgent` instead of constructing provider/model classes in-agent. Route behavior to `runtime.run_prompt(...)` so the profile engine is provider-agnostic and testable.

### Violation 2: Agent harness directly instantiates OpenAI provider/model internals

- **File:** `packages/rentl-agents/src/rentl_agents/harness.py:229`
- **Severity:** High
- **Evidence:**
  ```python
  provider = OpenAIProvider(
      base_url=self._config.base_url,
      api_key=self._config.api_key,
  )
  model = OpenAIChatModel(self._config.model_id, provider=provider)
  ```
- **Recommendation:** Move provider/model construction into a shared adapter (or injectable client factory) and pass a protocol-typed model runtime into the harness. Avoid hardcoding concrete classes in this execution loop.

### Violation 3: Rubric judge directly selects and builds external model/provider classes

- **File:** `packages/rentl-core/src/rentl_core/benchmark/judge.py:86`
- **Severity:** High
- **Evidence:**
  ```python
  provider = OpenRouterProvider(api_key=api_key)
  self.model = OpenRouterModel(model_id, provider=provider)
  ...
  provider = OpenAIProvider(base_url=base_url, api_key=api_key)
  self.model = OpenAIChatModel(model_id, provider=provider)
  ```
- **Recommendation:** Introduce a benchmark-specific protocol in core (or reuse `LlmRuntimeProtocol`) for judge execution, and inject an implementation from composition wiring to eliminate direct external-library dependency in benchmark logic.

### Violation 4: Core downloader uses `httpx.AsyncClient` directly for external retrieval

- **File:** `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:57`
- **Severity:** Medium
- **Evidence:**
  ```python
  async with httpx.AsyncClient(timeout=30.0) as client:
      response = await client.get(url)
  ```
- **Recommendation:** Define and inject an HTTP/storage downloader protocol in core for this component (or move this class to a dedicated infra adapter layer) so core logic depends on protocol abstractions and transport can be swapped or mocked safely.

## Compliant Examples

- `packages/rentl-core/src/rentl_core/ports/llm.py:11` — Core defines `LlmRuntimeProtocol`, with protocol method `run_prompt(...)`.
- `packages/rentl-core/src/rentl_core/llm/connection.py:122` — Connection flow accepts `runtime: LlmRuntimeProtocol` and calls only protocol methods.
- `packages/rentl-core/src/rentl_core/orchestrator.py:271` — Orchestrator dependencies are typed as protocol interfaces (e.g., `LogSinkProtocol`, `IngestAdapterProtocol`, `ArtifactStoreProtocol`, `RunStateStoreProtocol`).
- `packages/rentl-llm/src/rentl_llm/openai_runtime.py:27` — Concrete BYOK runtime cleanly implements `LlmRuntimeProtocol`.
- `packages/rentl-io/src/rentl_io/storage/filesystem.py:48` — Storage adapters implement protocol interfaces from core.

## Scoring Rationale

- **Coverage:** Most core and orchestration integrations (roughly 3/4 of checked boundary points) are protocol-based, but 4 direct adapter instantiations remain in production model/external-service paths.
- **Severity:** High-severity violations are clustered in model execution (agent runtime, harness, judge), so each impacts architecture flexibility across multiple command paths.
- **Trend:** Newer modules such as `rentl_llm` and orchestration wiring show clear protocol-driven design; older/legacy execution paths in agents and benchmark judge still use concrete clients.
- **Risk:** The direct bindings increase swap-cost for model providers and complicate deterministic testing and future refactors of model/download infrastructure.

Overall score: **82/100**.
