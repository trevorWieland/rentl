# Spec (19) Initial Phase Agent: QA — Style Guide Critic

## Overview

Create the first LLM-based QA agent: a **Style Guide Critic** that evaluates translations against a project's style guide. This agent identifies violations of tone, formality, terminology preferences, and localization conventions defined in the style guide.

The agent integrates with the existing QA phase infrastructure, running alongside deterministic checks and producing `QaIssue` records with `category = STYLE`.

## Key Design Decisions

| Aspect | Decision |
|--------|----------|
| **Focus** | Style guide adherence only (other QA agents in future specs) |
| **Output** | `QaIssue` with `category = STYLE` |
| **Style Guide Source** | Markdown file in project config (like `rentl.toml`) |
| **No Style Guide** | Returns empty issues list (graceful degradation) |
| **Work Unit** | Per-batch/chunk (no scene requirement) |

---

## Integration with Deterministic QA Checks (Spec 18)

The QA phase now has **two complementary validation approaches** that run together:

```
┌─────────────────────────────────────────────────────────────┐
│                      QA PHASE                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────┐  ┌──────────────────────────┐ │
│  │ DETERMINISTIC CHECKS    │  │ LLM-BASED AGENTS         │ │
│  │ (Spec 18 - DONE)        │  │ (Spec 19 - THIS SPEC)    │ │
│  ├─────────────────────────┤  ├──────────────────────────┤ │
│  │ • Line length           │  │ • Style Guide Critic     │ │
│  │ • Empty translation     │  │   (style violations)     │ │
│  │ • Whitespace issues     │  │                          │ │
│  │ • Unsupported chars     │  │ Future agents:           │ │
│  │                         │  │ • Accuracy checker       │ │
│  │ Category: FORMATTING    │  │ • Pronoun detector       │ │
│  │ Cost: FREE (no LLM)     │  │                          │ │
│  │ Speed: INSTANT          │  │ Category: STYLE          │ │
│  └───────────┬─────────────┘  │ Cost: LLM API calls      │ │
│              │                └───────────┬──────────────┘ │
│              │                            │                │
│              └──────────┬─────────────────┘                │
│                         ▼                                  │
│              ┌─────────────────────┐                       │
│              │ MERGED QaPhaseOutput │                       │
│              │ (all issues combined)│                       │
│              └─────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### Orchestrator Flow (already implemented in `orchestrator.py:783-861`)

```python
async def _run_qa(...):
    # 1. Run deterministic checks FIRST (fast, free)
    deterministic_issues = runner.run_checks(translated_lines)

    # 2. Run LLM-based QA agents (if configured)
    agent_outputs = await _run_agent_pool(self._qa_agents, inputs)

    # 3. Merge ALL issues into single output
    merged_output = _merge_qa_outputs_with_deterministic(
        run, target_language, agent_outputs, deterministic_issues
    )
```

### Key Integration Points

| Component | File | What It Does |
|-----------|------|--------------|
| Deterministic Runner | `rentl_core/qa/runner.py` | Runs formatting checks |
| LLM Agent Wrapper | `rentl_agents/wiring.py` | Runs style guide critic |
| Merge Function | `orchestrator.py` | Combines both into `QaPhaseOutput` |
| Output Schema | `rentl_schemas/qa.py` | `QaIssue` used by BOTH |

Both approaches produce the **same `QaIssue` type** — they differ only in `category`:
- Deterministic → `QaCategory.FORMATTING`
- Style Guide Critic → `QaCategory.STYLE`

---

## Tasks

### Task 1: Save Spec Documentation ✓

Create `agent-os/specs/2026-02-01-1800-initial-phase-agent-qa/` with:
- `plan.md` — This implementation plan
- `shape.md` — Shaping notes (scope, decisions, context)
- `standards.md` — Applicable standards
- `references.md` — Reference implementations

---

### Task 2: Create Sample Style Guide

**File:** `samples/style-guide.md`

Create a sample style guide with localization best practices for testing.

---

### Task 3: Create QA Phase Prompt

**File:** `packages/rentl-agents/prompts/phases/qa.toml`

Phase-level prompt for QA team with style guide enforcement principles.

---

### Task 4: Create StyleGuideViolation Output Schema

**File:** `packages/rentl-schemas/src/rentl_schemas/phases.py`

Add `StyleGuideViolation` and `StyleGuideViolationList` schemas.

---

### Task 5: Register StyleGuideViolation in Schema Registry

**File:** `packages/rentl-agents/src/rentl_agents/profiles/loader.py`

Update `_init_schema_registry()` to register new schemas.

---

### Task 6: Create Style Guide Critic TOML Profile

**File:** `packages/rentl-agents/agents/qa/style_guide_critic.toml`

TOML profile following the established agent pattern.

---

### Task 7: Create QA Phase Utilities Module

**Files:**
- `packages/rentl-agents/src/rentl_agents/qa/__init__.py`
- `packages/rentl-agents/src/rentl_agents/qa/lines.py`

Utility functions for line formatting, violation conversion, and output merging.

---

### Task 8: Create QA Agent Wrapper and Factory

**File:** `packages/rentl-agents/src/rentl_agents/wiring.py`

Add `QaStyleGuideCriticAgent` class and `create_qa_agent_from_profile()` factory.

---

### Task 9: Update Package Exports

**File:** `packages/rentl-agents/src/rentl_agents/__init__.py`

Export new QA-related symbols.

---

### Task 10: Update validate_agents.py — Full QA Validation

**File:** `scripts/validate_agents.py`

Add QA phase running BOTH deterministic and LLM-based checks.

---

### Task 11: Create Unit Tests

**Files:**
- `tests/unit/rentl-agents/qa/test_qa_utils.py`
- `tests/unit/rentl-agents/qa/test_style_guide_critic.py`

Target: >80% coverage, all tests < 250ms

---

### Task 12: Create Integration Tests

**Files:**
- `tests/integration/features/agents/style_guide_critic.feature`
- `tests/integration/agents/test_style_guide_critic.py`

BDD-style integration tests.

---

### Task 13: Verification — Run make all

Run `make all` to ensure all code passes quality checks.

---

## Critical Files to Modify/Create

| File | Action |
|------|--------|
| `samples/style-guide.md` | Create |
| `packages/rentl-agents/prompts/phases/qa.toml` | Create |
| `packages/rentl-schemas/src/rentl_schemas/phases.py` | Add schemas |
| `packages/rentl-agents/src/rentl_agents/profiles/loader.py` | Register schema |
| `packages/rentl-agents/agents/qa/style_guide_critic.toml` | Create |
| `packages/rentl-agents/src/rentl_agents/qa/__init__.py` | Create |
| `packages/rentl-agents/src/rentl_agents/qa/lines.py` | Create |
| `packages/rentl-agents/src/rentl_agents/wiring.py` | Add wrapper + factory |
| `packages/rentl-agents/src/rentl_agents/__init__.py` | Update exports |
| `scripts/validate_agents.py` | Add QA phase |
| `tests/unit/rentl-agents/qa/test_qa_utils.py` | Create |
| `tests/unit/rentl-agents/qa/test_style_guide_critic.py` | Create |
| `tests/integration/features/agents/style_guide_critic.feature` | Create |
| `tests/integration/agents/test_style_guide_critic.py` | Create |

---

## Standards Applied

- **testing/make-all-gate** — Verification required before completion
- **testing/three-tier-test-structure** — Unit/integration test folders
- **testing/test-timing-rules** — Unit <250ms, integration <5s
- **testing/bdd-for-integration-quality** — Given/When/Then style
- **python/async-first-design** — Agent execution is async
- **python/strict-typing-enforcement** — Strict Pydantic schemas
- **python/pydantic-only-schemas** — All I/O uses Pydantic
- **architecture/thin-adapter-pattern** — Agent is thin wrapper over ProfileAgent

---

## Verification

1. **Profile loading**: `load_agent_profile()` succeeds for style_guide_critic.toml
2. **Template validation**: All template variables are in allowed set
3. **Schema validation**: `StyleGuideViolation` validates with strict Pydantic
4. **Mock validation**: `python scripts/validate_agents.py --mock --phase qa` shows both QA types
5. **Deterministic + LLM**: Both produce `QaIssue` objects that merge cleanly
6. **Empty style guide**: LLM agent returns empty issues (deterministic still runs)
7. **Unit tests**: All pass in < 250ms
8. **Integration tests**: All BDD scenarios pass
9. **make all**: Format, lint, type, and unit tests all pass
