# References for Initial Phase Agent: QA

## Similar Implementations

### Spec 15: Context Agent (Scene Summarizer)

- **Location:** `agent-os/specs/2026-01-28-1630-initial-phase-agent-context/`
- **Relevance:** Establishes foundational agent patterns
- **Key patterns:**
  - Three-layer prompt architecture (root → phase → agent)
  - TOML-based agent profiles with versioning
  - Strict validation at initialization
  - Template variable validation

### Spec 16: Pretranslation Agent (Idiom Labeler)

- **Location:** `agent-os/specs/2026-02-01-1500-initial-phase-agent-pretranslation/`
- **Relevance:** Shows chunking pattern for batch processing
- **Key patterns:**
  - `IdiomAnnotation` schema pattern (similar to `StyleGuideViolation`)
  - Chunking lines for batch processing
  - Agent wrapper class with factory function
  - Phase utilities module structure

### Spec 18: Deterministic QA Checks

- **Location:** `agent-os/specs/2026-02-01-1200-deterministic-qa-checks/`
- **Relevance:** Shows QA phase integration and `QaIssue` output
- **Key patterns:**
  - `QaIssue` output schema
  - QA phase configuration
  - Orchestrator integration (`_run_qa`, `_merge_qa_outputs_with_deterministic`)
  - Registry pattern for extensible checks

## Key Files to Study

### Agent Profiles

- `packages/rentl-agents/agents/pretranslation/idiom_labeler.toml` — TOML profile pattern
- `packages/rentl-agents/agents/context/scene_summarizer.toml` — Scene requirement pattern

### Agent Wrappers

- `packages/rentl-agents/src/rentl_agents/wiring.py` — Agent wrapper classes and factories
- `packages/rentl-agents/src/rentl_agents/runtime.py` — ProfileAgent implementation

### QA Integration

- `packages/rentl-core/src/rentl_core/orchestrator.py:783-861` — QA phase execution
- `packages/rentl-core/src/rentl_core/qa/runner.py` — Deterministic QA runner
- `packages/rentl-schemas/src/rentl_schemas/qa.py` — QaIssue schema

### Phase Schemas

- `packages/rentl-schemas/src/rentl_schemas/phases.py` — QaPhaseInput/Output
- `packages/rentl-schemas/src/rentl_schemas/primitives.py:147-158` — QaCategory enum

### Validation Script

- `scripts/validate_agents.py` — Pattern for adding QA phase validation
