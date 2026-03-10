# OpenRouter Provider Routing

When using OpenRouter, validate provider compatibility before committing to pipeline runs. Providers change capabilities over time — never assume a provider works; test it.

## Rules

1. **Provider-qualified model IDs** — Always use `provider/model-name` format (e.g., `openai/gpt-oss-20b`), never bare names (`gpt-oss-20b`)
2. **`require_parameters = true`** — Always set this so OpenRouter only routes to providers that support all request parameters (tool_choice, response_format, etc.)
3. **Validate before running** — Before running a full pipeline with a new model/provider combination, run a small test request to confirm the provider supports structured output and all required parameters
4. **Whitelist validated providers** — After testing, use `only = ["validated-provider"]` to lock routing. Don't rely on OpenRouter's default routing, which may choose an incompatible provider.

```toml
[endpoint.openrouter_provider]
require_parameters = true
only = ["validated-provider"]  # only after confirming it works
```

## Common failure pattern

OpenRouter routes to a provider that doesn't support `tool_choice=required` or other request parameters. The failure surfaces mid-pipeline as an opaque API error, wasting the entire run. This is preventable by testing the model+provider combination upfront and whitelisting it.

## Why

Provider capabilities vary and change. Walk-spec demo hit 3 provider routing failures, each requiring manual debugging to identify the provider as root cause. The fix was always the same: test, find a working provider, whitelist it.
