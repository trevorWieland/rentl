# Spec (16) Initial Phase Agent: Pretranslation — Idiom Labeler

## Overview

Create the first agent for the Pretranslation phase: an **Idiom Labeler** that identifies idiomatic expressions (puns, wordplay, set phrases) requiring special translation handling.

This agent follows the TOML-based declarative pattern established by the Context phase's SceneSummarizer, producing `PretranslationAnnotation` records with `annotation_type = "idiom"`.

## Key Differences from Context Agent

| Aspect | Context (SceneSummarizer) | Pretranslation (IdiomLabeler) |
|--------|--------------------------|------------------------------|
| **Work Unit** | Per-scene (`scene_id` required) | Per-batch/chunk (no scene requirement) |
| **Output Type** | `SceneSummary` | `IdiomAnnotation` → `PretranslationAnnotation` |
| **Phase Input** | `ContextPhaseInput` | `PretranslationPhaseInput` |
| **Phase Output** | `ContextPhaseOutput` | `PretranslationPhaseOutput` |

---

## Tasks

### Task 1: Save Spec Documentation ✓

Create `agent-os/specs/2026-02-01-1500-initial-phase-agent-pretranslation/` with:
- `plan.md` — This implementation plan
- `shape.md` — Shaping notes (scope, decisions, context)
- `standards.md` — Applicable standards
- `references.md` — Reference implementations

### Task 2: Create Pretranslation Phase Prompt

**File:** `packages/rentl-agents/prompts/phases/pretranslation.toml`

```toml
phase = "pretranslation"
output_language = "source"

[system]
content = """
You are on the Pretranslation team. Your role is to analyze source text and identify
elements that require special attention during translation.

IMPORTANT: All your outputs must be written in {{source_lang}}, the same language
as the source text. You are annotating for translators, not translating yourself.

Your team's principles:
- Identify idiomatic expressions, puns, and wordplay
- Flag culturally-specific references
- Note linguistic patterns that don't translate literally
- Provide context and suggestions for translators
- Use consistent annotation terminology
"""
```

### Task 3: Create IdiomAnnotation Output Schema

**File:** `packages/rentl-schemas/src/rentl_schemas/phases.py`

Add new schema:
```python
class IdiomAnnotation(BaseSchema):
    """Single idiom annotation produced by the Idiom Labeler agent."""

    line_id: LineId = Field(..., description="Line identifier for the annotation")
    idiom_text: str = Field(..., min_length=1, description="The idiomatic expression found")
    idiom_type: str = Field(
        ...,
        pattern=r"^(pun|wordplay|set_phrase|cultural_reference|honorific_nuance|other)$",
        description="Type of idiom"
    )
    explanation: str = Field(..., min_length=1, description="Explanation of the idiom's meaning")
    translation_hint: str | None = Field(None, description="Optional translation suggestion")
```

### Task 4: Register IdiomAnnotation in Schema Registry

**File:** `packages/rentl-agents/src/rentl_agents/profiles/loader.py`

Update `_init_schema_registry()` to register `IdiomAnnotation`.

### Task 5: Create Idiom Labeler TOML Profile

**File:** `packages/rentl-agents/agents/pretranslation/idiom_labeler.toml`

```toml
[meta]
name = "idiom_labeler"
version = "1.0.0"
phase = "pretranslation"
description = "Identifies idiomatic expressions, puns, wordplay, and culturally-specific phrases"
output_schema = "IdiomAnnotation"

[requirements]
scene_id_required = false

[orchestration]
priority = 10
depends_on = []

[prompts.agent]
content = """
Your specific role is Idiom Identification.

For each batch of lines you analyze, identify:
1. Puns and wordplay that rely on multiple meanings
2. Set phrases and idioms that don't translate literally
3. Cultural references specific to the source culture
4. Honorific or speech level nuances
5. Any other expressions requiring special translation attention
...
"""

[prompts.user_template]
content = """
Analyze the following lines for idiomatic expressions and translation challenges.

Lines to analyze:
---
{{source_lines}}
---

Scene context (if available):
{{scene_summary}}
...
"""

[tools]
allowed = ["get_game_info"]

[model_hints]
recommended = ["gpt-5.2", "claude-4.5-sonnet", "nemotron-3-nano-30b-a3b"]
min_context_tokens = 8192
benefits_from_reasoning = false
```

### Task 6: Create Pretranslation Phase Utilities Module

**Files:**
- `packages/rentl-agents/src/rentl_agents/pretranslation/__init__.py`
- `packages/rentl-agents/src/rentl_agents/pretranslation/lines.py`

Functions:
- `chunk_lines(source_lines, chunk_size)` — Split lines for batch processing
- `format_lines_for_prompt(lines)` — Format lines with IDs for prompt injection
- `get_scene_summary_for_lines(lines, scene_summaries)` — Get relevant context
- `idiom_to_annotation(idiom)` — Convert `IdiomAnnotation` → `PretranslationAnnotation`
- `merge_idiom_annotations(run_id, idiom_annotations)` — Merge into `PretranslationPhaseOutput`

### Task 7: Create Pretranslation Agent Wrapper and Factory

**File:** `packages/rentl-agents/src/rentl_agents/wiring.py`

Add:
- `PretranslationIdiomLabelerAgent` class (chunks lines, runs ProfileAgent per chunk, merges results)
- `create_pretranslation_agent_from_profile()` factory function

### Task 8: Update Package Exports

**File:** `packages/rentl-agents/src/rentl_agents/__init__.py`

Export new symbols:
- `PretranslationIdiomLabelerAgent`
- `create_pretranslation_agent_from_profile`
- `chunk_lines`, `format_lines_for_prompt`, `merge_idiom_annotations`

### Task 9: Create Validation Script

**File:** `scripts/validate_idiom_labeler.py`

Following the pattern of `validate_scene_summarizer.py`:
- `--mock` mode for structure validation without LLM
- Real LLM mode with `rentl.toml` defaults
- `--input FILE` for batch testing with JSONL
- Displays `PretranslationAnnotation` results

### Task 10: Create Unit Tests

**File:** `tests/unit/rentl-agents/test_pretranslation.py`

Test classes:
- `TestChunkLines` — Line batching
- `TestFormatLinesForPrompt` — Prompt formatting
- `TestMergeIdiomAnnotations` — Result merging

Target: >80% coverage, all tests < 250ms

### Task 11: Create Integration Tests

**Files:**
- `tests/integration/features/agents/idiom_labeler.feature` — BDD scenarios
- `tests/integration/agents/test_idiom_labeler.py` — Step implementations

Scenarios:
- Load idiom labeler profile from TOML
- Create pretranslation agent from profile
- Validate template variables

### Task 12: Verification — Run make all

Run `make all` to ensure all code passes quality checks:
- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests

This task MUST pass before the spec is considered complete.

---

## Critical Files to Modify/Create

| File | Action |
|------|--------|
| `packages/rentl-agents/prompts/phases/pretranslation.toml` | Create |
| `packages/rentl-schemas/src/rentl_schemas/phases.py` | Add `IdiomAnnotation` |
| `packages/rentl-agents/src/rentl_agents/profiles/loader.py` | Register schema |
| `packages/rentl-agents/agents/pretranslation/idiom_labeler.toml` | Create |
| `packages/rentl-agents/src/rentl_agents/pretranslation/__init__.py` | Create |
| `packages/rentl-agents/src/rentl_agents/pretranslation/lines.py` | Create |
| `packages/rentl-agents/src/rentl_agents/wiring.py` | Add wrapper + factory |
| `packages/rentl-agents/src/rentl_agents/__init__.py` | Update exports |
| `scripts/validate_idiom_labeler.py` | Create |
| `tests/unit/rentl-agents/test_pretranslation.py` | Create |
| `tests/integration/features/agents/idiom_labeler.feature` | Create |
| `tests/integration/agents/test_idiom_labeler.py` | Create |

---

## Standards Applied

- **testing/make-all-gate** — Verification required before completion
- **testing/three-tier-test-structure** — Unit/integration test folders
- **testing/test-timing-rules** — Unit <250ms, integration <5s
- **python/async-first-design** — Agent execution is async
- **python/strict-typing-enforcement** — Strict Pydantic schemas
- **python/pydantic-only-schemas** — All I/O uses Pydantic
- **architecture/adapter-interface-protocol** — Implements PhaseAgentProtocol
- **ux/frictionless-by-default** — Opinionated defaults

---

## Verification

1. **Profile loading**: `load_agent_profile()` succeeds for idiom_labeler.toml
2. **Template validation**: All template variables are in allowed set
3. **Schema validation**: `IdiomAnnotation` validates with strict Pydantic
4. **Mock validation**: `python scripts/validate_idiom_labeler.py --mock` passes
5. **Real LLM test**: `python scripts/validate_idiom_labeler.py` produces valid annotations
6. **Unit tests**: All pass in < 250ms
7. **Integration tests**: All BDD scenarios pass
8. **make all**: Format, lint, type, and unit tests all pass
