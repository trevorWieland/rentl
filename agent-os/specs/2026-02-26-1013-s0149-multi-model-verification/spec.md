spec_id: s0.1.49
issue: https://github.com/trevorWieland/rentl/issues/144
version: v0.1

# Spec: Multi-Model Verification & Compatibility

## Problem
rentl supports BYOK model endpoints but has no systematic way to verify that specific models actually work through the full pipeline. Users must guess whether their model is compatible, and there's no regression safety net when provider APIs change.

## Goals
- Provide a data-driven registry of verified models (local and OpenRouter)
- Offer both a CLI command and a test suite for model compatibility verification
- Verify each model through a full mini 5-phase pipeline (context, pretranslation, translate, QA, edit)
- Make adding new verified models a zero-code-change operation
- Handle local model loading via LM Studio API automatically

## Non-Goals
- Performance benchmarking (that's s0.1.37)
- Translation quality evaluation (that's quality tests)
- Supporting non-OpenAI-compatible endpoints
- Auto-discovery of available models from providers

## Acceptance Criteria
- [ ] A verified-models TOML registry file exists listing all 9 models with endpoint type (local/openrouter), model_id, and per-model config overrides
- [ ] `rentl verify-models` CLI command exists, reads the registry, runs each model through a mini 5-phase pipeline on golden input data, and reports pass/fail per model per phase with actionable error messages
- [ ] A pytest quality test suite (`tests/quality/compatibility/`) parameterizes over the registry and runs the same mini-pipeline verification — no test skipping
- [ ] All 4 local models pass verification (via LM Studio model loading API): google/gemma-3-27b, qwen/qwen3-vl-30b, qwen/qwen3.5-35b-a3b, openai/gpt-oss-20b
- [ ] All 5 OpenRouter models pass verification: qwen/qwen3.5-27b, deepseek/deepseek-v3.2, z-ai/glm-5, openai/gpt-oss-120b, minimax/minimax-m2.5
- [ ] No model-specific branching in source code (grep for model name strings returns zero hits outside the registry and test fixtures)
- [ ] Adding a new model to the verified list requires only a registry file edit — no code changes
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Verified model registry must be data-driven** — The list of verified models lives in a declarative TOML file, not hardcoded in Python. Adding a new model to the verified list requires zero code changes.
2. **Each verified model must pass a full mini-pipeline** — Verification means running all 5 pipeline phases (context, pretranslation, translate, QA, edit) on a small input set with structured output validation. A model that only passes probe/connectivity is NOT verified.
3. **No test modifications to make models pass** — If a model fails structured output, the fix goes in provider handling or model config, never in relaxing test assertions.
4. **CLI and test suite share the same verification logic** — `rentl verify-models` and the pytest suite must use the same underlying runner. No parallel implementations that can drift.
5. **No hardcoded model-specific branches** — No `if "gpt" in model_name` or `if model_name == "qwen3.5"` anywhere in the source code. All model differences must be handled through declarative configuration, provider capabilities, or generic retry/fallback logic. This is non-negotiable — the codebase must remain model-agnostic.
