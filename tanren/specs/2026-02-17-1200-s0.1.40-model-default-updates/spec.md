spec_id: s0.1.40
issue: https://github.com/trevorWieland/rentl/issues/124
version: v0.1

# Spec: Model Default Updates

## Problem

The current model presets and hardcoded defaults across the codebase (`gpt-4-turbo`, `gpt-4o-mini`, `llama3.2`) are outdated or at end-of-life. These are what new users see on `rentl init` and what the runtime falls back to when no model is specified — giving a poor first impression and silently using models that may be deprecated.

## Goals

- Update all endpoint presets to current, well-supported models
- Make open-weight models the default recommendation for OpenRouter
- Remove silent model fallbacks — require explicit `model_id` in config
- Make the Local preset model-agnostic (not tied to Ollama)
- Eliminate all stale model string references across code, tests, docs, and config

## Non-Goals

- Adding new presets or providers (just updating existing ones)
- Changing the BYOK architecture or endpoint configuration flow
- Automatic model discovery or validation against provider APIs
- Changing model_hints in agent TOMLs that are already current

## Acceptance Criteria

- [ ] OpenRouter preset uses `qwen/qwen3-30b-a3b` as default model
- [ ] OpenAI-direct preset uses `gpt-5-nano` as default model
- [ ] Local preset is renamed from "Local (Ollama)" to "Local" with `default_model=None`
- [ ] CLI `init` flow prompts user for model name when preset has no default model
- [ ] `ProfileAgentConfig.model_id` and `AgentHarnessConfig.model_id` have no default value; omitting raises a validation error with a clear message
- [ ] README, benchmark config descriptions, error messages, and agent TOML `model_hints` reference current models
- [ ] `frictionless-by-default.md` standard updated with current model references
- [ ] All test files updated to use consistent, current model strings
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No EOL models in presets** — No preset may reference a model with an announced end-of-life date or a model that has already been superseded by its provider
2. **Open-weight default on OpenRouter** — The OpenRouter preset must default to an open-weight model, not a proprietary one
3. **Local preset has no default model** — `default_model` must be `None`; the CLI must prompt the user to provide their own
4. **No silent model fallbacks** — `model_id` must be required in `ProfileAgentConfig` and `AgentHarnessConfig` with no default value; missing model_id must raise a clear error
5. **All model string references updated** — No stale model strings (`gpt-4-turbo`, `gpt-4o-mini`, `llama3.2`) remain anywhere in production code, tests, docs, or config files (historical spec docs excluded)
