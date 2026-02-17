# Demo: Model Default Updates

Model defaults have been updated to current, well-supported models. Running `rentl init` now recommends open-weight models by default, requires explicit model selection for local setups, and the runtime rejects configs that omit `model_id` entirely. This matters because outdated defaults undermine user trust and the BYOK philosophy — every model choice should be intentional.

## Environment

- API keys: not needed (no LLM calls in demo)
- External services: none required
- Setup: `make install` (ensure dependencies are up to date)

## Steps

1. **[RUN]** Run `rentl init` in a fresh temp directory, select the **OpenRouter** preset — expected: `rentl.toml` contains `model_id = "qwen/qwen3-30b-a3b"` and `base_url` points to `https://openrouter.ai/api/v1`

2. **[RUN]** Run `rentl init` in a fresh temp directory, select the **OpenAI** preset — expected: `rentl.toml` contains `model_id = "gpt-5-nano"` and `base_url` points to `https://api.openai.com/v1`

3. **[RUN]** Run `rentl init` in a fresh temp directory, select the **Local** preset and provide a custom model name when prompted — expected: preset is named "Local" (not "Local (Ollama)"), user is prompted for model name, `rentl.toml` contains the user-provided model

4. **[RUN]** Attempt to instantiate `ProfileAgentConfig` and `AgentHarnessConfig` without `model_id` — expected: Pydantic `ValidationError` with a clear message indicating `model_id` is required

5. **[RUN]** Search the entire codebase for stale model strings (`gpt-4-turbo`, `gpt-4o-mini`, `llama3.2`) — expected: zero matches in production code, tests, docs, and config files (historical spec docs excluded)

## Results

(Appended by run-demo — do not write this section during shaping)
