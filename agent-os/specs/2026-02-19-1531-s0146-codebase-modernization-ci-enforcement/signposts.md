# Signposts

- **Task:** Task 2 (audit round 1)
- **Status:** resolved
- **Resolution:** do-task round 2 (2026-02-19) — added `Field(description=...)` to all 9 migrated models
- **Problem:** The dataclass-to-Pydantic migration left multiple schema fields as raw annotations instead of `Field(..., description=...)`.
- **Evidence:** `ProviderCapabilities` uses raw fields (`name: str`, `is_openrouter: bool`, etc.) at `packages/rentl-llm/src/rentl_llm/providers.py:28`, `packages/rentl-llm/src/rentl_llm/providers.py:29`, `packages/rentl-llm/src/rentl_llm/providers.py:30`, and `packages/rentl-llm/src/rentl_llm/providers.py:31`.
- **Evidence:** Additional migrated models also use raw schema annotations, including `ProjectContext` (`packages/rentl-agents/src/rentl_agents/tools/game_info.py:19`), `_AgentCacheEntry` (`packages/rentl-agents/src/rentl_agents/factory.py:108`), `PromptLayerRegistry` (`packages/rentl-agents/src/rentl_agents/layers.py:64`), `PromptComposer` (`packages/rentl-agents/src/rentl_agents/layers.py:467`), `TemplateContext` (`packages/rentl-agents/src/rentl_agents/templates.py:274`), `AgentPoolBundle` (`packages/rentl-agents/src/rentl_agents/wiring.py:1107`), and `_AgentProfileSpec` (`packages/rentl-agents/src/rentl_agents/wiring.py:1117`).
- **Impact:** This violates `pydantic-only-schemas` and `strict-typing-enforcement` and can be repeated in later dataclass migration tasks if not corrected now.
- **Solution:** For each migrated schema field, replace raw annotations with `Field` declarations that include clear `description` metadata and validators where constraints are known.

- **Task:** Task 3 (audit round 1)
- **Status:** resolved
- **Resolution:** do-task round 2 (2026-02-19) — added `extra="forbid"` to all 6 Task 3 migrated models
- **Problem:** Migrated BaseModels silently ignore unknown constructor kwargs, which changes dataclass constructor behavior and can hide bad call-site inputs.
- **Evidence:** `DeterministicCheckResult` currently uses `ConfigDict(frozen=True)` without `extra="forbid"` at `packages/rentl-core/src/rentl_core/qa/protocol.py:30`.
- **Evidence:** Audit command output shows unknown kwargs are accepted and dropped: `DeterministicCheckResult(..., unexpected='extra')` constructs successfully and `model_extra= None`.
- **Impact:** This is a behavioral regression against the original dataclass constructors (which reject unknown kwargs), violating Task 3's public API preservation requirement and risking silent misconfiguration.
- **Solution:** Add `extra="forbid"` to `model_config` (or equivalent strict-extra configuration) for each Task 3 migrated model at `packages/rentl-core/src/rentl_core/llm/connection.py:44`, `packages/rentl-core/src/rentl_core/orchestrator.py:242`, `packages/rentl-core/src/rentl_core/orchestrator.py:2036`, `packages/rentl-core/src/rentl_core/qa/protocol.py:30`, `scripts/validate_agents.py:117`, and `scripts/validate_agents.py:127`.

- **Task:** Task 4
- **Status:** resolved
- **Resolution:** do-task round 1 (2026-02-19) — migrated 8 of 16 test dataclasses; 8 evaluator subclasses retained as dataclasses
- **Problem:** 8 evaluator subclasses in `tests/quality/agents/evaluators.py` inherit from `pydantic_evals.evaluators.Evaluator`, which is itself a `@dataclass(repr=False)` with a custom `_StrictABCMeta` metaclass. Converting these to `BaseModel` would break the inheritance chain and the library's serialization machinery.
- **Evidence:** `Evaluator` is defined at `.venv/lib/python3.14/site-packages/pydantic_evals/evaluators/evaluator.py:138` as `@dataclass(repr=False) class Evaluator(Generic[InputsT, OutputT, MetadataT], metaclass=_StrictABCMeta)`. It uses `dataclasses.fields(self)` internally at line 290 in `build_serialization_arguments`.
- **Impact:** The 8 evaluator subclasses (`OutputFieldPresent`, `ListFieldMinLength`, `OutputListIdsMatch`, `ToolCallCountAtLeast`, `ToolResultHasKeys`, `ToolInputSchemaValid`, `ToolInputHasType`, `ToolInputStringMinLength`) must remain as `@dataclass` to inherit correctly from their third-party parent. This is not a compliance gap — these are framework-mandated dataclasses, not application schemas.
- **Solution:** The remaining 8 test dataclasses (`QualityModelConfig`, `ToolCallRecorder`, 5 `EvalContext` classes, `FakeAgent`) were migrated to `BaseModel` with `ConfigDict(extra="forbid")` and `Field(description=...)`. The evaluator subclasses are correctly left as `@dataclass`.
- **Files affected:** `tests/quality/agents/evaluators.py` (unchanged), `tests/quality/agents/quality_harness.py`, `tests/quality/agents/tool_spy.py`, `tests/quality/agents/test_translate_agent.py`, `tests/quality/agents/test_edit_agent.py`, `tests/quality/agents/test_context_agent.py`, `tests/quality/agents/test_pretranslation_agent.py`, `tests/quality/agents/test_qa_agent.py`, `tests/unit/rentl-agents/test_alignment_retries.py`
