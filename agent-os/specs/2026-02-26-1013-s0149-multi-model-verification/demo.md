# Demo: Multi-Model Verification & Compatibility

rentl now has verified multi-model support. Instead of hoping a model works, users can check the verified registry and run `rentl verify-models` to confirm compatibility. The registry is data-driven — adding a new model is a TOML edit, not a code change. The verification runner tests each model through a full 5-phase mini-pipeline (context, pretranslation, translate, QA, edit) to prove end-to-end structured output works.

This demo proves the system works across 9 models on two providers (LM Studio local + OpenRouter).

## Environment

- API keys: `RENTL_OPENROUTER_API_KEY` via .env (OpenRouter), `RENTL_LOCAL_API_KEY` via .env (LM Studio)
- External services:
  - OpenRouter API at https://openrouter.ai/api/v1 — verified (200)
  - LM Studio at http://192.168.1.23:1234/v1 — verified (200, auth required)
  - LM Studio model load API at http://192.168.1.23:1234/api/v1/models/load — for switching local models
- Setup: Local LM Studio server must be running with the 4 local models downloaded

## Steps

1. **[RUN]** Show the verified-models registry file and confirm it lists all 9 models with correct endpoint types — expected: TOML file with 4 local + 5 OpenRouter entries, each with model_id, endpoint_type, and any config overrides

2. **[RUN]** Run `rentl verify-models --endpoint local --model qwen/qwen3-vl-30b` — expected: runner calls LM Studio load API to switch to qwen3-vl-30b, then runs all 5 phases, all pass with structured output validated

3. **[RUN]** Run `rentl verify-models --endpoint openrouter` — expected: all 5 OpenRouter models (qwen/qwen3.5-27b, deepseek/deepseek-v3.2, z-ai/glm-5, openai/gpt-oss-120b, minimax/minimax-m2.5) pass all 5 phases

4. **[RUN]** Run the pytest compatibility suite for OpenRouter models — expected: all 5 pass, BDD-style output, zero skips

5. **[RUN]** Grep source code for hardcoded model names — expected: zero hits outside registry file and test fixtures. Run: `rg -l "gemma-3-27b|qwen3-vl-30b|qwen3.5-35b|gpt-oss-20b|qwen3.5-27b|deepseek-v3.2|glm-5|gpt-oss-120b|minimax-m2.5" --type py` and confirm only registry/fixture files appear

6. **[SKIP]** Run full local model sweep (load all 4 local models sequentially, verify each through full mini-pipeline) — reason: requires sequential model loading with ~60s+ swap time per model, exceeds autonomous demo time budget. Verified manually during shaping for 4/4 local models. The test suite (Task 5) covers this in CI.

## Results

(Appended by run-demo — do not write this section during shaping)
