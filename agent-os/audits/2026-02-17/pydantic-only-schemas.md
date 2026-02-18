---
standard: pydantic-only-schemas
category: python
score: 76
importance: High
violations_count: 13
date: 2026-02-18
status: violations-found
---

# Standards Audit: Pydantic-Only Schemas

**Standard:** `python/pydantic-only-schemas`
**Date:** 2026-02-18
**Score:** 76/100
**Importance:** High

## Summary

Most schema-like types are correctly centralized under `rentl_schemas` and use Pydantic. However, several production modules still define data carriers with `@dataclass` and a few internal/script-level containers that cross module boundaries without `BaseModel`/`BaseSchema` validation and serialization guarantees. The compliance is broadly high-level consistent in external contracts, but the remaining drift is concentrated in orchestration/state and agent-wiring paths that should be part of the same schema discipline.

## Violations

### Violation 1: Dataclass used for run-time provider capability schema

- **File:** `packages/rentl-agents/src/rentl_agents/providers.py:14`
- **Severity:** Medium
- **Evidence:**
  ```python
  @dataclass(frozen=True)
  class ProviderCapabilities:
      name: str
      is_openrouter: bool
      supports_tool_calling: bool
      supports_tool_choice_required: bool
  ```
- **Recommendation:** Replace with a Pydantic model, for example `class ProviderCapabilities(BaseSchema):` with `Field(..., description=...)`.

### Violation 2: Dataclass used for project context passed through tool contract

- **File:** `packages/rentl-agents/src/rentl_agents/tools/game_info.py:13`
- **Severity:** Medium
- **Evidence:**
  ```python
  @dataclass
  class ProjectContext:
      game_name: str = "Unknown Game"
      synopsis: str | None = None
      source_language: str = "ja"
      target_languages: list[str] = field(default_factory=list)
  ```
- **Recommendation:** Model this as a Pydantic schema and validate tool inputs/outputs consistently at execution boundaries.

### Violation 3: Dataclass used for tool registry state container

- **File:** `packages/rentl-agents/src/rentl_agents/tools/registry.py:67`
- **Severity:** Low
- **Evidence:**
  ```python
  @dataclass
  class ToolRegistry:
      _tools: dict[str, AgentToolProtocol] = field(default_factory=dict)
  ```
- **Recommendation:** Use a lightweight Pydantic model (`BaseSchema`) for stored registry state if persisted/interchanged, or keep this as a pure internal class with private methods only and no external data contract wording.

### Violation 4: Dataclass used for internal agent cache entry with typed payload

- **File:** `packages/rentl-agents/src/rentl_agents/factory.py:101`
- **Severity:** Low
- **Evidence:**
  ```python
  @dataclass
  class _AgentCacheEntry[OutputT: BaseSchema]:
      agent: AgentHarness[BaseSchema, OutputT]
      output_type: type[OutputT]
  ```
- **Recommendation:** Replace with `BaseSchema` if cached state is serialized or passed across boundaries; otherwise keep non-schema internals and avoid storing validated payload shapes here.

### Violation 5: Dataclass used for prompt layer registry payload

- **File:** `packages/rentl-agents/src/rentl_agents/layers.py:58`
- **Severity:** Medium
- **Evidence:**
  ```python
  @dataclass
  class PromptLayerRegistry:
      root: RootPromptConfig | None = None
      phases: dict[PhaseName, PhasePromptConfig] = field(default_factory=dict)
  ```
- **Recommendation:** Replace with Pydantic `BaseSchema` to enforce/serialize registry shape consistently across prompt-loading code paths.

### Violation 6: Dataclass used for prompt composition context

- **File:** `packages/rentl-agents/src/rentl_agents/templates.py:267`
- **Severity:** Medium
- **Evidence:**
  ```python
  @dataclass
  class TemplateContext:
      root_variables: dict[str, str] = field(default_factory=dict)
      phase_variables: dict[str, str] = field(default_factory=dict)
      agent_variables: dict[str, str] = field(default_factory=dict)
  ```
- **Recommendation:** Convert to Pydantic and validate required/allowed variable keys when rendering templates.

### Violation 7: Dataclass used for prompt composer state

- **File:** `packages/rentl-agents/src/rentl_agents/layers.py:461`
- **Severity:** Low
- **Evidence:**
  ```python
  @dataclass
  class PromptComposer:
      registry: PromptLayerRegistry
      separator: str = "\n\n---\n\n"
  ```
- **Recommendation:** Use a Pydantic schema if this object is ever persisted, copied, or reconstructed from external config.

### Violation 8: Dataclass used for agent profile wiring payloads

- **File:** `packages/rentl-agents/src/rentl_agents/wiring.py:1086`
- **Severity:** Low
- **Evidence:**
  ```python
  @dataclass(slots=True)
  class AgentPoolBundle:
      context_agents: list[tuple[str, ContextAgentPoolProtocol]]
      pretranslation_agents: list[tuple[str, PretranslationAgentPoolProtocol]]
      translate_agents: list[tuple[str, TranslateAgentPoolProtocol]]
      qa_agents: list[tuple[str, QaAgentPoolProtocol]]
      edit_agents: list[tuple[str, EditAgentPoolProtocol]]
  ```
- **Recommendation:** Convert to a pydantic model when used as a typed contract between pipeline setup and execution layers.

### Violation 9: Dataclass used for orchestration profile spec

- **File:** `packages/rentl-agents/src/rentl_agents/wiring.py:1097`
- **Severity:** Low
- **Evidence:**
  ```python
  @dataclass(frozen=True, slots=True)
  class _AgentProfileSpec:
      name: str
      profile: AgentProfileConfig
      path: Path
  ```
- **Recommendation:** Prefer Pydantic for config-like spec objects, especially where loaded from filesystem and used in control flow.

### Violation 10: Dataclass used for core run-context state

- **File:** `packages/rentl-core/src/rentl_core/orchestrator.py:239`
- **Severity:** High
- **Evidence:**
  ```python
  @dataclass(slots=True)
  class PipelineRunContext:
      run_id: RunId
      config: RunConfig
      progress: RunProgress
      created_at: Timestamp
      started_at: Timestamp | None = None
      ...
  ```
- **Recommendation:** Convert to a schema model (`BaseSchema`/`BaseModel`) to enforce validation, support JSON persistence, and protect run-state transitions across phase boundaries.

### Violation 11: Dataclass used for deterministic QA result payload

- **File:** `packages/rentl-core/src/rentl_core/qa/protocol.py:17`
- **Severity:** High
- **Evidence:**
  ```python
  @dataclass(frozen=True, slots=True)
  class DeterministicCheckResult:
      line_id: LineId
      category: QaCategory
      severity: QaSeverity
      message: str
      suggestion: str | None = None
      metadata: dict[str, JsonValue] | None = None
  ```
- **Recommendation:** Replace with Pydantic output model so QA result schemas are validated and serializable with consistent field constraints.

### Violation 12: Dataclass used for LLM connection planning target

- **File:** `packages/rentl-core/src/rentl_core/llm/connection.py:40`
- **Severity:** Medium
- **Evidence:**
  ```python
  @dataclass(frozen=True)
  class LlmConnectionTarget:
      runtime: LlmRuntimeSettings
      phases: tuple[PhaseName, ...]
  ```
- **Recommendation:** Replace with `BaseSchema` and validate phase/runtime references before connection checks.

### Violation 13: Dataclass used for CLI helper resolution config in a script

- **File:** `scripts/validate_agents.py:116`
- **Severity:** Low
- **Evidence:**
  ```python
  @dataclass(frozen=True, slots=True)
  class _ResolvedConfig:
      config: RunConfig
      config_path: Path
      workspace_dir: Path
      agents_dir: Path
      prompts_dir: Path
  ```
- **Recommendation:** Even in script-only paths, prefer Pydantic models for schema-like resolved config to avoid drift and keep validation consistent with runtime usage.

## Compliant Examples

- `packages/rentl-schemas/src/rentl_schemas/io.py:18` — `IngestSource(BaseSchema)` uses `Field(..., description=...)` and inherits Pydantic base.
- `packages/rentl-schemas/src/rentl_schemas/config.py:25` — `ProjectPaths(BaseSchema)` demonstrates typed validation with explicit `Field` descriptions.
- `packages/rentl-schemas/src/rentl_schemas/phases.py:23` — `SceneSummary(BaseSchema)` shows strict schema modeling for phase outputs.

## Scoring Rationale

- **Coverage:** Approximately 13 explicit non-Pydantic schema-like `@dataclass` declarations were found among active runtime and utility modules that carry structured data, versus the project’s large Pydantic-first schema surface. Estimated compliance is around 75%.
- **Severity:** Higher-severity issues are concentrated in orchestration and QA result structures (`PipelineRunContext`, `DeterministicCheckResult`) that cross execution boundaries and may affect persisted state and reporting.
- **Trend:** The repository is not fully consistent; runtime modules in both `rentl-core` and `rentl-agents` still rely on dataclasses for core structures while most public API types in `rentl-schemas` are already Pydantic.
- **Risk:** Mixed model styles increase the chance of unchecked values, inconsistent serialization, and difficult schema evolution, especially for persisted run state and QA diagnostics.
