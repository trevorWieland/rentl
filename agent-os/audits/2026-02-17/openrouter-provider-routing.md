---
standard: openrouter-provider-routing
category: architecture
score: 42
importance: High
violations_count: 3
date: 2026-02-17
status: violations-found
---

# Standards Audit: OpenRouter Provider Routing

**Standard:** `architecture/openrouter-provider-routing`
**Date:** 2026-02-17
**Score:** 42/100
**Importance:** High

## Summary

OpenRouter integrations have partial adherence: request-parameter enforcement (`require_parameters`) is present, but provider-routing hardening is incomplete. The code allows non-qualified model IDs to flow into OpenRouter requests, does not enforce or require allowlisting with `only`, and never performs a compatibility preflight before full pipeline execution. These gaps create a realistic risk of mid-run provider mismatch failures and operational instability.

## Violations

### Violation 1: Provider-qualified model IDs are not required or validated

- **File:** `packages/rentl-schemas/src/rentl_schemas/llm.py:40-44`
- **Severity:** High
- **Evidence:**
  ```python
  class LlmModelSettings(BaseModel):
      """Runtime model settings for a provider."""
      model_id: str
  ```
  ```python
  response = await self._client.chat.completions.create(
      model=request.runtime.model.model_id,
      messages=request.messages,
      **base_params,
  )
  ```
  (`packages/rentl-llm/src/rentl_llm/openai_runtime.py:55-57`)
- **Recommendation:** Add validation that rejects non-qualified IDs for OpenRouter endpoints (for example with a regex like `^[^/]+/.+`). Convert/normalize at config boundary so all OpenRouter model IDs are in `provider/model` format. Example:
  ```toml
  [endpoint.openrouter_provider]
  model = "openai/gpt-5-nano"
  ```
  or via code-level validation in `ModelEndpointConfig` / schema layer.

### Violation 2: Provider allowlist (`only`) is defined but never applied for routing

- **File:** `packages/rentl-schemas/src/rentl_schemas/config.py:178-181`
- **Severity:** High
- **Evidence:**
  ```python
  class OpenRouterProviderRoutingConfig(BaseModel):
      only: Optional[list[str]] = None
      require_parameters: bool = True
  ```
  ```python
  kwargs = model.openrouter_provider.model_dump(exclude_none=True)
  provider_settings["openrouter_provider"] = kwargs
  ```
  (`packages/rentl-llm/src/rentl_llm/openai_runtime.py:137-142`)
  ```python
  settings = {
      "openrouter_provider": model.openrouter_provider.model_dump(exclude_none=True),
  }
  ```
  (`packages/rentl-agents/src/rentl_agents/runtime.py:527-537`)
  In pipeline/benchmark override paths, only `require_parameters` is set and `only` is not populated (`services/rentl-cli/src/rentl/main.py:1455-1466`).
- **Recommendation:** Require explicit `only` in validated OpenRouter configs and enforce it in runtime payload construction. For first-class flows, populate `only = ["validated-provider"]` after compatibility checks and reject configs that omit allowlisted providers in OpenRouter contexts.

### Violation 3: No preflight compatibility validation for provider capability before running pipelines

- **File:** `services/rentl-cli/src/rentl/main.py:915-923`
- **Severity:** Critical
- **Evidence:**
  ```python
  async def run_pipeline(
      config, **kwargs
  ):
      pipeline = await self._load_pipeline(...)
      if not await self._check_api_key_configured(api_key_name=api_key_name):
          return ExitCode.ERROR
      await self._run_pipeline_async(pipeline, config, **kwargs)
  ```
  (`services/rentl-cli/src/rentl/main.py:915-923`, `_run_pipeline_async:2811-2835`)
  ```python
  async def _ensure_api_key(self, ...):
      # validates env key existence only
      return bool(os.environ.get(api_key_name))
  ```
  (`services/rentl-cli/src/rentl/main.py:2326-2359`)
  The existing connectivity check sends only a basic hello-world request and does not validate OpenRouter-specific capability combinations (`tool_choice`, `response_format`, etc.) (`services/rentl-cli/src/rentl/main.py:2061-2069`).
- **Recommendation:** Add a preflight step for new model/provider pairs before full pipeline execution that sends a minimal request covering required params (tool calls, structured output/response format) and fails fast with targeted message. Gate pipeline start on passing this compatibility probe.

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/config.py:166-168` — `OpenRouterProviderRoutingConfig.require_parameters` defaults to `True` and direct validation enforces it.
- `tests/integration/byok/test_openrouter_runtime.py:69` — asserts `require_parameters` is `True` in the constructed OpenRouter request.
- `tests/unit/schemas/test_config.py:350-359` — config validation defaults `require_parameters` to `True` when missing.

## Scoring Rationale

- **Coverage:** 3 of 4 standard requirements are only partially implemented; routing hardening (`only`) and preflight validation are effectively absent in runtime execution paths.
- **Severity:** Critical preflight gap plus two High routing risks keep score low due to the operational impact of mid-pipeline provider incompatibility errors.
- **Trend:** Mixed; newer and older paths both share the same unguarded behavior. Some code quality has improved for `require_parameters`, but that has not translated into full provider-routing compliance.
- **Risk:** High practical risk of non-deterministic or mid-run failures when OpenRouter selects unsupported providers for structured-output/tooling requests.
