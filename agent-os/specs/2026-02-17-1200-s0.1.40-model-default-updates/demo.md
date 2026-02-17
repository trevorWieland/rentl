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

### Run 1 — Post-implementation (2026-02-17 15:30)
- Step 1 [RUN]: PASS — `rentl init` with OpenRouter preset produces `model_id = "qwen/qwen3-30b-a3b"` and `base_url = "https://openrouter.ai/api/v1"` in rentl.toml
- Step 2 [RUN]: PASS — `rentl init` with OpenAI preset produces `model_id = "gpt-5-nano"` and `base_url = "https://api.openai.com/v1"` in rentl.toml
- Step 3 [RUN]: PASS — Preset displayed as "Local" (not "Local (Ollama)"), user prompted for "Model ID:", rentl.toml contains `model_id = "my-custom-model-7b"` (the user-provided value)
- Step 4 [RUN]: PASS — `ProfileAgentConfig(agent_name='test', system_prompt='test')` raises `ValidationError: model_id Field required`; `AgentHarnessConfig(agent_name='test', system_prompt='test', base_url='...', api_key='test')` raises `ValidationError: model_id Field required`
- Step 5 [RUN]: PASS — grep for `gpt-4-turbo|gpt-4o-mini|llama3.2` returns 15 matches, all exclusively in `agent-os/specs/` (historical spec docs) and `agent-os/product/roadmap.md` (spec description). Zero matches in production code, tests, docs, or config files.
- **Overall: PASS**
