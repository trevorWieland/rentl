# References for Initial QA Checks (Deterministic)

## Similar Implementations

### Existing Phase Agent Wrappers

- **Location:** `packages/rentl-agents/src/rentl_agents/wiring.py`
- **Relevance:** Shows how phase agents are structured, configured, and integrated
- **Key patterns:**
  - Wrapper classes that handle sharding/chunking
  - Configuration via TOML profiles
  - Result conversion to phase output schemas

### QA Schemas

- **Location:** `packages/rentl-schemas/src/rentl_schemas/qa.py`
- **Relevance:** Defines `QaIssue`, `QaSummary` that deterministic checks must produce
- **Key patterns:**
  - `QaIssue` structure: issue_id, line_id, category, severity, message, suggestion, metadata
  - `QaSummary` aggregation: total_issues, by_category, by_severity
  - `QaCategory` enum: GRAMMAR, TERMINOLOGY, STYLE, CONSISTENCY, FORMATTING, CONTEXT, CULTURAL, OTHER
  - `QaSeverity` enum: INFO, MINOR, MAJOR, CRITICAL

### Phase Configuration Schemas

- **Location:** `packages/rentl-schemas/src/rentl_schemas/config.py`
- **Relevance:** Shows how phase configuration is structured
- **Key patterns:**
  - `PhaseConfig` with phase name, enabled flag, parameters dict
  - `PhaseExecutionConfig` for execution strategy
  - Parameters stored as `dict[str, JsonValue]` for flexibility

### Orchestrator Integration

- **Location:** `packages/rentl-core/src/rentl_core/orchestrator.py`
- **Relevance:** Shows how phases are executed and outputs merged
- **Key patterns:**
  - Phase execution methods (`_run_context`, `_run_qa`, etc.)
  - Config extraction helpers (`_get_phase_config`)
  - Output merging patterns
  - Error handling with `OrchestrationError`

### Primitive Types

- **Location:** `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- **Relevance:** Defines core type aliases used throughout
- **Key types:**
  - `LineId` (HumanReadableId)
  - `IssueId` (Uuid7)
  - `QaCategory`, `QaSeverity` enums
  - `JsonValue` for arbitrary JSON data
