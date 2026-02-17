spec_id: s0.1.40
issue: https://github.com/trevorWieland/rentl/issues/124
version: v0.1

# Plan: Model Default Updates

## Decision Record

The current model presets (`gpt-4-turbo`, `gpt-4o-mini`, `llama3.2`) are outdated. New users hitting `rentl init` get EOL model suggestions, and the runtime silently falls back to `gpt-4o-mini` when no model is configured. This undermines the BYOK philosophy — users should always make an explicit choice. The fix is straightforward: update presets to current models, require explicit `model_id` in config, and sweep all stale references.

Model choices:
- OpenRouter: `qwen/qwen3-30b-a3b` (open-weight, efficient MoE)
- OpenAI: `gpt-5-nano` (current generation, cost-effective)
- Local: no default (user provides their own)

## Tasks

- [x] Task 1: Save Spec Documentation
- [x] Task 2: Update endpoint presets in init.py
  - Change OpenRouter `default_model` from `"openai/gpt-4-turbo"` to `"qwen/qwen3-30b-a3b"`
  - Change OpenAI `default_model` from `"gpt-4-turbo"` to `"gpt-5-nano"`
  - Rename `"Local (Ollama)"` to `"Local"`, set `default_model` to `None`
  - Update `EndpointPreset.default_model` type from `str` to `str | None`
  - Update `InitAnswers.model_id` field description example
  - Update `tests/unit/core/test_init.py` (~14 occurrences of old model strings)
  - Acceptance: `ENDPOINT_PRESETS` contains only current models; `EndpointPreset.default_model` accepts `None`; unit tests pass
- [x] Task 3: Handle None default_model in CLI init flow
  - Update `services/rentl-cli/src/rentl/main.py` init flow: when preset has `default_model=None`, prompt user for model name instead of silently using None
  - Update `tests/unit/cli/test_main.py` (4 occurrences of old model strings)
  - Update `tests/integration/cli/test_init.py` (2 occurrences of old model strings)
  - Acceptance: selecting Local preset prompts for model; selecting OpenRouter/OpenAI presets auto-fills model; CLI tests pass
- [ ] Task 4: Remove model_id defaults from runtime configs
  - `packages/rentl-agents/src/rentl_agents/runtime.py`: remove `"gpt-4o-mini"` default from `ProfileAgentConfig.model_id`, make it a required field with clear validation error
  - `packages/rentl-agents/src/rentl_agents/harness.py`: remove `"gpt-4o-mini"` default from `AgentHarnessConfig.model_id`, make it a required field with clear validation error
  - Update unit tests: `test_wiring.py`, `test_runtime_telemetry.py`, `test_profile_agent_execute.py`, `test_profile_agent_run_errors.py`, `test_alignment_retries.py`
  - Update integration tests: `test_direct_translator.py`, `test_idiom_labeler.py`, `test_profile_loading.py`, `test_style_guide_critic.py`
  - Acceptance: instantiating configs without `model_id` raises `ValidationError`; all agent tests pass with explicit model_id
- [ ] Task 5: Update documentation, TOML model_hints, and remaining references
  - `packages/rentl-agents/agents/qa/style_guide_critic.toml` (both copies): update model_hints from `gpt-4o`/`claude-3.5-sonnet`/`claude-3-opus` to current models matching other TOMLs
  - `README.md`: update example config model reference
  - `packages/rentl-agents/README.md`: update documentation example
  - `packages/rentl-schemas/src/rentl_schemas/benchmark/config.py`: update field description
  - `scripts/validate_agents.py`: update example usage
  - `agent-os/standards/ux/frictionless-by-default.md`: update model references
  - Update `tests/unit/benchmark/test_judge.py` (10 occurrences), `tests/integration/benchmark/test_cli_command.py`, `tests/integration/benchmark/test_judge_flow.py`
  - Acceptance: `grep -r` for `gpt-4-turbo`, `gpt-4o-mini`, `llama3.2` returns zero matches outside historical spec docs; all benchmark tests pass
