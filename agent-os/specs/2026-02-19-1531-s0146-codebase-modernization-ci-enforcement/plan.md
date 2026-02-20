spec_id: s0.1.46
issue: https://github.com/trevorWieland/rentl/issues/133
version: v0.1

# Plan: Codebase Modernization & CI Enforcement

## Decision Record

The codebase has 30+ violations across 9 standards identified by a standards audit (2026-02-17). Rather than incremental fixes, this spec addresses all violations in a single sweep to achieve full compliance. Dataclass migration is split across three tasks (agents, core, tests) to manage risk — the core orchestrator classes are high-impact and need extra care. Modern Python conversions and strict typing follow after migration is stable. CI and remaining standards fixes are grouped last since they're independent.

## Tasks

- [x] Task 1: Save Spec Documentation
- [x] Task 2: Migrate rentl-agents dataclasses to Pydantic (9 classes, 6 files)
  - `ProviderCapabilities` — `packages/rentl-llm/src/rentl_llm/providers.py:15` (note: issue lists wrong path)
  - `ProjectContext` — `packages/rentl-agents/src/rentl_agents/tools/game_info.py:13`
  - `ToolRegistry` — `packages/rentl-agents/src/rentl_agents/tools/registry.py:67`
  - `_AgentCacheEntry` — `packages/rentl-agents/src/rentl_agents/factory.py:101`
  - `PromptLayerRegistry` — `packages/rentl-agents/src/rentl_agents/layers.py:58`
  - `PromptComposer` — `packages/rentl-agents/src/rentl_agents/layers.py:461`
  - `TemplateContext` — `packages/rentl-agents/src/rentl_agents/templates.py:267`
  - `AgentPoolBundle` — `packages/rentl-agents/src/rentl_agents/wiring.py:1101`
  - `_AgentProfileSpec` — `packages/rentl-agents/src/rentl_agents/wiring.py:1112`
  - Use `model_config = ConfigDict(frozen=True)` or `ConfigDict(slots=True)` to match original behavior
  - Preserve public API — field names, types, and defaults must not change
  - Remove `from dataclasses import dataclass` imports when no longer needed
  - Run `make check` to verify
  - [x] Fix: `ProviderCapabilities` uses raw schema annotations instead of `Field(..., description=...)`, violating `pydantic-only-schemas` and `strict-typing-enforcement` (`packages/rentl-llm/src/rentl_llm/providers.py:28`, `packages/rentl-llm/src/rentl_llm/providers.py:29`, `packages/rentl-llm/src/rentl_llm/providers.py:30`, `packages/rentl-llm/src/rentl_llm/providers.py:31`) (audit round 1)
  - [x] Fix: Add `Field(..., description=...)` (and validators where applicable) for migrated schema fields in `ProjectContext`, `_AgentCacheEntry`, `PromptLayerRegistry`, `PromptComposer`, `TemplateContext`, `AgentPoolBundle`, and `_AgentProfileSpec` to satisfy `pydantic-only-schemas` and `strict-typing-enforcement` (`packages/rentl-agents/src/rentl_agents/tools/game_info.py:19`, `packages/rentl-agents/src/rentl_agents/factory.py:108`, `packages/rentl-agents/src/rentl_agents/layers.py:64`, `packages/rentl-agents/src/rentl_agents/layers.py:467`, `packages/rentl-agents/src/rentl_agents/templates.py:274`, `packages/rentl-agents/src/rentl_agents/wiring.py:1107`, `packages/rentl-agents/src/rentl_agents/wiring.py:1117`) (audit round 1; see signposts.md: Task 2, migrated models missing Field metadata)
  - [x] Fix: Restore dataclass constructor strictness for all Task 2 migrated models by adding `extra="forbid"` (or equivalent) so unknown kwargs raise instead of being silently dropped (`packages/rentl-llm/src/rentl_llm/providers.py:26`, `packages/rentl-agents/src/rentl_agents/tools/game_info.py:13`, `packages/rentl-agents/src/rentl_agents/tools/registry.py:73`, `packages/rentl-agents/src/rentl_agents/factory.py:106`, `packages/rentl-agents/src/rentl_agents/layers.py:58`, `packages/rentl-agents/src/rentl_agents/layers.py:465`, `packages/rentl-agents/src/rentl_agents/templates.py:268`, `packages/rentl-agents/src/rentl_agents/wiring.py:1105`, `packages/rentl-agents/src/rentl_agents/wiring.py:1125`; audit evidence: `uv run python` constructor probes accept `unexpected=` for `ProviderCapabilities`, `ProjectContext`, `ToolRegistry`, `PromptLayerRegistry`, `PromptComposer`, `TemplateContext`, and `AgentPoolBundle`) (audit round 2)
- [x] Task 3: Migrate rentl-core + scripts dataclasses to Pydantic (6 classes, 5 files)
  - **`PipelineRunContext`** — `packages/rentl-core/src/rentl_core/orchestrator.py:238` (high-impact: core run state)
  - Unlisted dataclass — `packages/rentl-core/src/rentl_core/orchestrator.py:2006`
  - **`DeterministicCheckResult`** — `packages/rentl-core/src/rentl_core/qa/protocol.py:17` (high-impact: QA output)
  - `LlmConnectionTarget` — `packages/rentl-core/src/rentl_core/llm/connection.py:40`
  - `_ResolvedConfig` — `scripts/validate_agents.py:116`
  - Unlisted dataclass — `scripts/validate_agents.py:125`
  - Extra care on PipelineRunContext and DeterministicCheckResult — used extensively
  - Preserve public API and any `slots=True`, `frozen=True` behavior
  - Run `make check` to verify
  - [x] Fix: Configure all Task 3 migrated BaseModels to reject unknown input fields (e.g., `model_config = ConfigDict(extra="forbid", ...)`) so constructor behavior matches prior dataclasses and unknown kwargs do not get silently dropped (`packages/rentl-core/src/rentl_core/llm/connection.py:44`, `packages/rentl-core/src/rentl_core/orchestrator.py:242`, `packages/rentl-core/src/rentl_core/orchestrator.py:2036`, `packages/rentl-core/src/rentl_core/qa/protocol.py:30`, `scripts/validate_agents.py:117`, `scripts/validate_agents.py:127`) (audit round 1; see signposts.md: Task 3, unknown kwargs silently ignored after dataclass migration)
- [ ] Task 4: Migrate test code dataclasses to Pydantic (16 occurrences, 8 files)
  - `tests/quality/agents/evaluators.py` — 8 dataclasses
  - `tests/quality/agents/quality_harness.py:18`
  - `tests/quality/agents/tool_spy.py:19`
  - `tests/quality/agents/test_translate_agent.py:46`
  - `tests/quality/agents/test_edit_agent.py:48`
  - `tests/quality/agents/test_context_agent.py:46`
  - `tests/quality/agents/test_pretranslation_agent.py:48`
  - `tests/quality/agents/test_qa_agent.py:45`
  - `tests/unit/rentl-agents/test_alignment_retries.py:40`
  - Run `make check` to verify
  - [x] Fix: Replace `object` annotations in `FakeAgent` with concrete types for `outputs`, `contexts`, `update_context`, and `run` to satisfy `strict-typing-enforcement` (`tests/unit/rentl-agents/test_alignment_retries.py:45`, `tests/unit/rentl-agents/test_alignment_retries.py:48`, `tests/unit/rentl-agents/test_alignment_retries.py:54`, `tests/unit/rentl-agents/test_alignment_retries.py:58`) (audit round 1)
  - [ ] Fix: Replace raw Pydantic field annotations with `Field(..., description=...)` in test schemas `MockInput` and `MockOutput` to satisfy `strict-typing-enforcement` (`tests/unit/rentl-agents/test_factory.py:19`, `tests/unit/rentl-agents/test_factory.py:20`, `tests/unit/rentl-agents/test_factory.py:26`, `tests/unit/rentl-agents/test_factory.py:27`) (audit round 2)
- [x] Task 5: Convert if/elif to match/case + modern Python cleanup (8+ violations, 5+ files)
  - `packages/rentl-core/src/rentl_core/orchestrator.py:499` — 7-branch if/elif phase dispatch
  - `packages/rentl-core/src/rentl_core/orchestrator.py:1776` — phase-guard chains
  - `packages/rentl-agents/src/rentl_agents/wiring.py:1288` — 5-branch if/elif
  - `services/rentl-cli/src/rentl/main.py:2696` — phase branching in hydration
  - `packages/rentl-agents/src/rentl_agents/prompts.py:183` — `{**d1, **d2}` to `d1 | d2`
  - `services/rentl-cli/src/rentl/main.py:2335` — isinstance chain to match/case
  - Sweep for any additional legacy if/elif or dict merge patterns
  - Run `make check` to verify
- [x] Task 6: Enable ty strict mode + fix type annotations
  - Enable ty strict mode in `pyproject.toml:61`
  - Replace `object` annotations in `packages/rentl-schemas/src/rentl_schemas/version.py` (5 comparison methods)
  - Replace `object` annotations in `packages/rentl-schemas/src/rentl_schemas/config.py` (6 coerce validators)
  - Replace `object` annotations in `packages/rentl-core/src/rentl_core/migrate.py:227`
  - Replace `object` annotations in `services/rentl-cli/src/rentl/main.py:4011`
  - Replace `object` annotations in test files where applicable
  - Resolve any new ty errors introduced by strict mode
  - Run `make check` to verify
  - [x] Fix: Replace remaining `Any`/`object` annotations in tests to satisfy `strict-typing-enforcement` (`tests/unit/schemas/test_validation.py:3`, `tests/unit/schemas/test_validation.py:37`, `tests/unit/schemas/test_validation.py:231`, `tests/unit/schemas/test_validation.py:244`, `packages/rentl-core/tests/unit/core/test_migrate.py:279`, `packages/rentl-core/tests/unit/core/test_migrate.py:289`) (audit round 1)
- [x] Task 7: Create CI workflow + deprecation warnings enforcement
  - Create `.github/workflows/ci.yml` that runs `make all` on pull requests to main
  - Configure as required status check for merge blocking
  - Add `-W error::DeprecationWarning` to pytest `addopts` in `pyproject.toml:71`
  - Add deprecation warning flag to Makefile test targets at `Makefile:69`
  - Run `make check` to verify
  - [x] Fix: Enforce CI merge blocking by configuring required status checks/ruleset for `main` so `.github/workflows/ci.yml` `make all` job must pass before merge (`.github/workflows/ci.yml:3`, `.github/workflows/ci.yml:13`; audit evidence: `gh api repos/trevorWieland/rentl/branches/main/protection` returns `404 Branch not protected` and `gh api repos/trevorWieland/rentl/rulesets` returns `[]`) (audit round 1)
- [x] Task 8: Standards compliance sweep (ID formats, API envelope, placeholders, dependency versions)
  - `HeadToHeadResult.line_id` — change type from `str` to `LineId` at `packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:20`
  - Runtime `run_id` — validate as UUIDv7 at `packages/rentl-agents/src/rentl_agents/runtime.py:594`
  - Health endpoint — wrap in `ApiResponse` envelope at `services/rentl-api/src/rentl_api/main.py:16`
  - Placeholder artifact path — replace hardcoded `placeholder.*` at `packages/rentl-core/src/rentl_core/orchestrator.py:1488`
  - Obsolete test stub — replace pass-only stub at `tests/unit/benchmark/test_config.py:129`
  - Dependency versions — add upper major bounds in `pyproject.toml:9,10` and package pyproject.toml files
  - Install instructions — add `--upgrade` flag at `Makefile:43`, update `README.md:37` if needed
  - Final sweep for any remaining violations across all 9 standards
  - Run `make all` to verify full compliance
