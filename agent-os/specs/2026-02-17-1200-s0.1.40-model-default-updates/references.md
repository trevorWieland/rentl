# References: Model Default Updates

## Implementation Files

### Production Code
- `packages/rentl-core/src/rentl_core/init.py` — ENDPOINT_PRESETS, EndpointPreset schema, InitAnswers
- `services/rentl-cli/src/rentl/main.py` — CLI init flow, preset selection
- `packages/rentl-agents/src/rentl_agents/runtime.py` — ProfileAgentConfig.model_id default
- `packages/rentl-agents/src/rentl_agents/harness.py` — AgentHarnessConfig.model_id default

### Agent TOML
- `packages/rentl-agents/agents/qa/style_guide_critic.toml` — outdated model_hints
- `packages/rentl-agents/src/rentl_agents/agents/qa/style_guide_critic.toml` — outdated model_hints (src copy)

### Documentation
- `README.md` — example config model reference
- `packages/rentl-agents/README.md` — documentation example
- `packages/rentl-schemas/src/rentl_schemas/benchmark/config.py` — field description
- `scripts/validate_agents.py` — example usage
- `agent-os/standards/ux/frictionless-by-default.md` — model references

### Test Files
- `tests/unit/core/test_init.py` — ~14 occurrences
- `tests/unit/cli/test_main.py` — 4 occurrences
- `tests/integration/cli/test_init.py` — 2 occurrences
- `tests/unit/rentl-agents/test_wiring.py`
- `tests/unit/rentl-agents/test_runtime_telemetry.py`
- `tests/unit/rentl-agents/test_profile_agent_execute.py`
- `tests/unit/rentl-agents/test_profile_agent_run_errors.py`
- `tests/unit/rentl-agents/test_alignment_retries.py`
- `tests/integration/agents/test_direct_translator.py`
- `tests/integration/agents/test_idiom_labeler.py`
- `tests/integration/agents/test_profile_loading.py`
- `tests/integration/agents/test_style_guide_critic.py`
- `tests/unit/benchmark/test_judge.py` — 10 occurrences
- `tests/integration/benchmark/test_cli_command.py`
- `tests/integration/benchmark/test_judge_flow.py`

## Issues
- https://github.com/trevorWieland/rentl/issues/124

## Related Specs
- s0.1.29 — BYOK Runtime Integration (dependency: established ProfileAgentConfig)
- s0.1.13 — CLI Workflow Phase Selection (dependency: established CLI init flow)
- s0.1.14 — BYOK Config Endpoint Validation (dependency: established endpoint presets)
- s0.1.37 — Benchmark Harness (already removed gpt-4o-mini from judge default)
