# References: Codebase Modernization & CI Enforcement

## Issue
- https://github.com/trevorWieland/rentl/issues/133

## Standards Documents
- `agent-os/standards/python/pydantic-only-schemas.md`
- `agent-os/standards/python/modern-python-314.md`
- `agent-os/standards/python/strict-typing-enforcement.md`
- `agent-os/standards/testing/make-all-gate.md`
- `agent-os/standards/global/address-deprecations-immediately.md`
- `agent-os/standards/global/no-placeholder-artifacts.md`
- `agent-os/standards/global/prefer-dependency-updates.md`
- `agent-os/standards/architecture/id-formats.md`
- `agent-os/standards/architecture/api-response-format.md`

## Source Audit
- `agent-os/audits/2026-02-17/`

## Key Implementation Files

### Dataclass Migrations (Production)
- `packages/rentl-llm/src/rentl_llm/providers.py` — ProviderCapabilities
- `packages/rentl-agents/src/rentl_agents/tools/game_info.py` — ProjectContext
- `packages/rentl-agents/src/rentl_agents/tools/registry.py` — ToolRegistry
- `packages/rentl-agents/src/rentl_agents/factory.py` — _AgentCacheEntry
- `packages/rentl-agents/src/rentl_agents/layers.py` — PromptLayerRegistry, PromptComposer
- `packages/rentl-agents/src/rentl_agents/templates.py` — TemplateContext
- `packages/rentl-agents/src/rentl_agents/wiring.py` — AgentPoolBundle, _AgentProfileSpec
- `packages/rentl-core/src/rentl_core/orchestrator.py` — PipelineRunContext + 1 unlisted
- `packages/rentl-core/src/rentl_core/qa/protocol.py` — DeterministicCheckResult
- `packages/rentl-core/src/rentl_core/llm/connection.py` — LlmConnectionTarget
- `scripts/validate_agents.py` — _ResolvedConfig + 1 unlisted

### Dataclass Migrations (Test)
- `tests/quality/agents/evaluators.py` — 8 dataclasses
- `tests/quality/agents/quality_harness.py`
- `tests/quality/agents/tool_spy.py`
- `tests/quality/agents/test_translate_agent.py`
- `tests/quality/agents/test_edit_agent.py`
- `tests/quality/agents/test_context_agent.py`
- `tests/quality/agents/test_pretranslation_agent.py`
- `tests/quality/agents/test_qa_agent.py`
- `tests/unit/rentl-agents/test_alignment_retries.py`

### Modern Python Conversions
- `packages/rentl-core/src/rentl_core/orchestrator.py:499,1776` — if/elif phase dispatch
- `packages/rentl-agents/src/rentl_agents/wiring.py:1288` — if/elif phase branching
- `services/rentl-cli/src/rentl/main.py:2335,2696` — isinstance chain + phase branching
- `packages/rentl-agents/src/rentl_agents/prompts.py:183` — dict merge

### Typing
- `packages/rentl-schemas/src/rentl_schemas/version.py` — object annotations
- `packages/rentl-schemas/src/rentl_schemas/config.py` — object annotations
- `packages/rentl-core/src/rentl_core/migrate.py` — object annotation
- `services/rentl-cli/src/rentl/main.py` — object annotation
- `pyproject.toml` — ty config

### CI & Build
- `.github/workflows/` — CI workflow (to be created)
- `pyproject.toml` — pytest config, dependency versions
- `Makefile` — test targets, install targets

### Standards Compliance
- `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py` — LineId type
- `packages/rentl-agents/src/rentl_agents/runtime.py` — UUIDv7 validation
- `services/rentl-api/src/rentl_api/main.py` — ApiResponse envelope
- `packages/rentl-core/src/rentl_core/orchestrator.py:1488` — placeholder artifact
- `tests/unit/benchmark/test_config.py:129` — test stub
