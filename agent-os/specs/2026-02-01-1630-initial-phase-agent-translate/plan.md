# Spec (17) Initial Phase Agent: Translate — Direct Translator

## Overview

Create the first agent for the Translate phase: a **Direct Translator** that produces translated lines using simple direct translation. This agent takes context data (scene summaries) and pretranslation data (idiom annotations) as input, and outputs `TranslatedLine` records.

This agent follows the TOML-based declarative pattern established by Context (SceneSummarizer) and Pretranslation (IdiomLabeler) phases.

## Key Differences from Pretranslation Agent

| Aspect | Pretranslation (IdiomLabeler) | Translate (DirectTranslator) |
|--------|------------------------------|------------------------------|
| **Purpose** | Annotate source text | Produce translated text |
| **Work Unit** | Per-batch/chunk | Per-batch/chunk |
| **Output Type** | `IdiomAnnotationList` | `TranslationResult` (list of `TranslatedLine`) |
| **Phase Input** | `PretranslationPhaseInput` | `TranslatePhaseInput` |
| **Phase Output** | `PretranslationPhaseOutput` | `TranslatePhaseOutput` |
| **Output Language** | Source language | Target language |
| **Additional Context** | Scene summaries | Scene summaries + idiom annotations + glossary |

---

## Tasks

### Task 1: Save Spec Documentation ✓

Create `agent-os/specs/2026-02-01-1630-initial-phase-agent-translate/` with:
- `plan.md` — This implementation plan
- `shape.md` — Shaping notes (scope, decisions, context)
- `standards.md` — Applicable standards
- `references.md` — Reference implementations

### Task 2: Create Translate Phase Prompt

**File:** `packages/rentl-agents/prompts/phases/translate.toml`

```toml
phase = "translate"
output_language = "target"

[system]
content = """
You are on the Translation team. Your role is to produce accurate, natural-sounding
translations that preserve the original meaning, tone, and emotional impact.

IMPORTANT: All your outputs must be written in {{target_lang}}, the target language
for this localization project.

Your team's principles:
- Preserve meaning and intent over literal translation
- Maintain character voice and speaking style
- Apply glossary terms consistently
- Consider pretranslation annotations for idioms and cultural references
- Ensure natural flow in the target language
- Match the register and formality of the original

The translations you produce will be reviewed by QA and Edit teams before final
delivery. Focus on accuracy and readability.
"""
```

### Task 3: Create TranslationResult Output Schema

**File:** `packages/rentl-schemas/src/rentl_schemas/phases.py`

Add new schema for LLM output:
```python
class TranslationResultLine(BaseSchema):
    """Single translated line in LLM output format."""

    line_id: LineId = Field(..., description="Line identifier matching the source")
    text: str = Field(..., min_length=1, description="Translated text content")
    notes: str | None = Field(None, description="Optional translator notes")


class TranslationResult(BaseSchema):
    """Translation result from the Direct Translator agent.

    This wrapper schema allows the LLM to return multiple translated lines
    from a batch of source lines.
    """

    translations: list[TranslationResultLine] = Field(
        ...,
        min_length=1,
        description="List of translated lines",
    )
```

### Task 4: Register TranslationResult in Schema Registry

**File:** `packages/rentl-agents/src/rentl_agents/profiles/loader.py`

Update `_init_schema_registry()` to register `TranslationResult`:
```python
from rentl_schemas.phases import TranslationResult

# In _init_schema_registry():
register_output_schema("TranslationResult", TranslationResult)
```

### Task 5: Create Direct Translator TOML Profile

**File:** `packages/rentl-agents/agents/translate/direct_translator.toml`

```toml
# Direct Translator Agent Profile
# Produces translated lines using simple direct translation.

[meta]
name = "direct_translator"
version = "1.0.0"
phase = "translate"
description = "Produces translated lines using simple direct translation with context awareness"
output_schema = "TranslationResult"

[requirements]
scene_id_required = false

[orchestration]
priority = 10
depends_on = []

[prompts.agent]
content = """
Your specific role is Direct Translation.

For each batch of source lines, produce accurate translations that:
1. Preserve the original meaning and intent
2. Sound natural in the target language
3. Maintain character voice and speaking patterns
4. Apply any glossary terms provided
5. Consider pretranslation notes for idioms and special expressions

Translation guidelines:
- Match the formality level of the original
- Preserve punctuation style appropriate to the target language
- Keep line lengths reasonable for game text display
- Maintain consistency with previous translations in the same scene

For each line, provide:
- line_id: The exact ID from the source line (do not modify)
- text: Your translation of the source text
- notes: (optional) Any notes about translation choices made
"""

[prompts.user_template]
content = """
Translate the following lines from {{source_lang}} to {{target_lang}}.

Source lines ({{line_count}} total):
---
{{source_lines}}
---

Scene context:
{{scene_summary}}

Pretranslation notes (idioms, cultural references to handle carefully):
{{pretranslation_notes}}

Glossary (use these translations):
{{glossary_terms}}

Return your translations as a list. Each translation must include:
- line_id: The exact line ID from the source
- text: Your translation in {{target_lang}}
- notes: (optional) Notes about your translation choices
"""

[tools]
allowed = ["get_game_info"]

[model_hints]
recommended = ["gpt-5.2", "claude-4.5-sonnet", "nemotron-3-nano-30b-a3b", "gpt-oss-20b"]
min_context_tokens = 16384
benefits_from_reasoning = false
```

### Task 6: Create Translate Phase Utilities Module

**Files:**
- `packages/rentl-agents/src/rentl_agents/translate/__init__.py`
- `packages/rentl-agents/src/rentl_agents/translate/lines.py`

Functions in `lines.py`:
```python
def chunk_lines(source_lines: list[SourceLine], chunk_size: int = 50) -> list[list[SourceLine]]:
    """Split source lines into batches for processing."""

def format_lines_for_prompt(lines: list[SourceLine]) -> str:
    """Format source lines for prompt injection.

    Format: [line_id] [speaker]: text
    or:     [line_id]: text
    """

def get_scene_summary_for_lines(
    lines: list[SourceLine],
    scene_summaries: list[SceneSummary] | None,
) -> str:
    """Get relevant scene summaries for a batch of lines.

    Returns "(No scene context available)" if no summaries match.
    """

def format_pretranslation_annotations(
    lines: list[SourceLine],
    annotations: list[PretranslationAnnotation] | None,
) -> str:
    """Format pretranslation annotations for the lines being translated.

    Returns "(No pretranslation notes)" if no annotations available.
    Filters to only annotations for the given lines.
    """

def format_glossary_terms(glossary: list[GlossaryTerm] | None) -> str:
    """Format glossary terms for prompt injection.

    Returns "(No glossary terms)" if glossary is empty/None.
    Format: "term → translation (notes)" or "term → translation"
    """

def translation_result_to_lines(
    result: TranslationResult,
    source_lines: list[SourceLine],
) -> list[TranslatedLine]:
    """Convert LLM TranslationResult to TranslatedLine records.

    Copies metadata from source lines (route_id, scene_id, speaker, source_columns).
    Sets source_text from the original source line.
    """

def merge_translated_lines(
    run_id: RunId,
    target_language: LanguageCode,
    translated_lines: list[TranslatedLine],
) -> TranslatePhaseOutput:
    """Package translated lines into TranslatePhaseOutput."""
```

### Task 7: Create Translate Agent Wrapper and Factory

**File:** `packages/rentl-agents/src/rentl_agents/wiring.py`

Add:
```python
class TranslateDirectTranslatorAgent:
    """Translate phase agent that produces translations using a ProfileAgent.

    This agent:
    1. Chunks source lines into batches for processing
    2. Formats context (scene summaries, pretranslation annotations, glossary)
    3. Runs ProfileAgent for each chunk to produce TranslationResult
    4. Converts results to TranslatedLine and merges into TranslatePhaseOutput
    """

    def __init__(
        self,
        profile_agent: ProfileAgent[TranslatePhaseInput, TranslationResult],
        config: ProfileAgentConfig,
        chunk_size: int = 50,
        source_lang: LanguageCode = "ja",
        target_lang: LanguageCode = "en",
    ) -> None: ...

    async def run(self, payload: TranslatePhaseInput) -> TranslatePhaseOutput: ...


def create_translate_agent_from_profile(
    profile_path: Path,
    prompts_dir: Path,
    config: ProfileAgentConfig,
    tool_registry: ToolRegistry | None = None,
    chunk_size: int = 50,
    source_lang: LanguageCode = "ja",
    target_lang: LanguageCode = "en",
) -> TranslateDirectTranslatorAgent:
    """Create a translate phase agent from a TOML profile."""
```

### Task 8: Update Package Exports

**File:** `packages/rentl-agents/src/rentl_agents/__init__.py`

Export new symbols:
```python
from rentl_agents.wiring import (
    TranslateDirectTranslatorAgent,
    create_translate_agent_from_profile,
)
from rentl_agents.translate.lines import (
    chunk_lines as translate_chunk_lines,
    format_lines_for_prompt as translate_format_lines,
    format_pretranslation_annotations,
    format_glossary_terms,
    translation_result_to_lines,
    merge_translated_lines,
)
```

### Task 9: Expand Validation Script

**File:** `scripts/validate_agents.py`

Extend the existing validation script to include the translate phase:
- Add `"translate"` to `--phase` choices: `["all", "context", "pretranslation", "translate"]`
- Load the `direct_translator.toml` profile
- Add Step 6: Translate phase
  - Create `TranslateDirectTranslatorAgent` from profile
  - Build `TranslatePhaseInput` with:
    - `source_lines` from input
    - `scene_summaries` from context phase (if run)
    - `pretranslation_annotations` from pretranslation phase (if run)
    - `target_language` from config
  - Display translated lines with source comparison
  - Show any translator notes
- Update step numbering to accommodate new phase

### Task 10: Create Unit Tests

**File:** `tests/unit/rentl-agents/test_translate.py`

Test classes:
- `TestChunkLines` — Line batching (shared pattern with pretranslation)
- `TestFormatLinesForPrompt` — Prompt formatting
- `TestFormatPretranslationAnnotations` — Annotation formatting
- `TestFormatGlossaryTerms` — Glossary formatting
- `TestTranslationResultToLines` — Result conversion with metadata copying
- `TestMergeTranslatedLines` — Result merging into phase output

Target: >80% coverage, all tests < 250ms

### Task 11: Create Integration Tests

**Files:**
- `tests/integration/features/agents/direct_translator.feature` — BDD scenarios
- `tests/integration/agents/test_direct_translator.py` — Step implementations

Scenarios:
- Load direct translator profile from TOML
- Create translate agent from profile
- Validate template variables are in allowed set
- Process input with mock LLM

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
| `packages/rentl-agents/prompts/phases/translate.toml` | Create |
| `packages/rentl-schemas/src/rentl_schemas/phases.py` | Add `TranslationResult`, `TranslationResultLine` |
| `packages/rentl-agents/src/rentl_agents/profiles/loader.py` | Register schema |
| `packages/rentl-agents/agents/translate/direct_translator.toml` | Create |
| `packages/rentl-agents/src/rentl_agents/translate/__init__.py` | Create |
| `packages/rentl-agents/src/rentl_agents/translate/lines.py` | Create |
| `packages/rentl-agents/src/rentl_agents/wiring.py` | Add wrapper + factory |
| `packages/rentl-agents/src/rentl_agents/__init__.py` | Update exports |
| `scripts/validate_agents.py` | Expand with translate phase |
| `tests/unit/rentl-agents/test_translate.py` | Create |
| `tests/integration/features/agents/direct_translator.feature` | Create |
| `tests/integration/agents/test_direct_translator.py` | Create |

---

## Standards Applied

- **testing/make-all-gate** — Verification required before completion
- **testing/three-tier-test-structure** — Unit/integration test folders
- **testing/test-timing-rules** — Unit <250ms, integration <5s
- **python/async-first-design** — Agent execution is async
- **python/strict-typing-enforcement** — Strict Pydantic schemas
- **python/pydantic-only-schemas** — All I/O uses Pydantic
- **architecture/adapter-interface-protocol** — Implements PhaseAgentProtocol
- **ux/frictionless-by-default** — Opinionated defaults (chunk_size, languages)

---

## Verification

1. **Profile loading**: `load_agent_profile()` succeeds for direct_translator.toml
2. **Template validation**: All template variables are in allowed set
3. **Schema validation**: `TranslationResult` validates with strict Pydantic
4. **Mock validation**: `uv run python scripts/validate_agents.py --mock --phase translate` passes
5. **Translate only**: `uv run python scripts/validate_agents.py --phase translate` produces valid translations
6. **Full pipeline with sample data**: `uv run python scripts/validate_agents.py --input samples/golden/script.jsonl` runs all phases (context → pretranslation → translate) on real data
7. **Unit tests**: All pass in < 250ms
8. **Integration tests**: All BDD scenarios pass
9. **make all**: Format, lint, type, and unit tests all pass

---

## Design Notes

### Why "Direct Translator" naming?
The spec mentions "future translation agents would involve extra features like selective usage of other MTL models as tool calls." This first agent is called `direct_translator` to distinguish it from future agents that might use ensemble approaches, retrieval-augmented translation, or MTL model tools.

### Chunk size rationale
Default chunk size of 50 lines matches the pretranslation agent. For translation, this balances:
- Context coherence (nearby lines often relate)
- Token limits (translated text + context fits in typical context windows)
- Throughput (not too many API calls)

### Metadata preservation
The `translation_result_to_lines()` function must copy metadata from source lines to translated lines:
- `route_id`, `scene_id`, `speaker` — for downstream processing
- `source_columns` — for export compatibility
- `source_text` — set from the original source line text
