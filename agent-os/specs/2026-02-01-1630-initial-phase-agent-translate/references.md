# References for Initial Phase Agent: Translate

## Similar Implementations

### Context Phase — SceneSummarizer

- **Location:** `packages/rentl-agents/agents/context/scene_summarizer.toml`
- **Wiring:** `packages/rentl-agents/src/rentl_agents/wiring.py` → `ContextSceneSummarizerAgent`
- **Relevance:** Established the TOML profile pattern, 3-layer prompts, and wrapper class pattern
- **Key patterns:**
  - Per-scene processing with template context updates
  - Factory function `create_context_agent_from_profile()`
  - Schema registration in loader.py

### Pretranslation Phase — IdiomLabeler

- **Location:** `packages/rentl-agents/agents/pretranslation/idiom_labeler.toml`
- **Wiring:** `packages/rentl-agents/src/rentl_agents/wiring.py` → `PretranslationIdiomLabelerAgent`
- **Utilities:** `packages/rentl-agents/src/rentl_agents/pretranslation/lines.py`
- **Relevance:** Most recent and closest pattern — chunk-based processing without scene_id requirement
- **Key patterns:**
  - `chunk_lines()` for batch processing
  - `format_lines_for_prompt()` for prompt injection
  - Result merging into phase output
  - Scene summary lookup for context

## Related Specs

- **2026-01-28-1630-initial-phase-agent-context** — SceneSummarizer spec
- **2026-02-01-1500-initial-phase-agent-pretranslation** — IdiomLabeler spec

## Schema References

- **Input:** `TranslatePhaseInput` in `packages/rentl-schemas/src/rentl_schemas/phases.py`
- **Output:** `TranslatePhaseOutput` in `packages/rentl-schemas/src/rentl_schemas/phases.py`
- **Line schema:** `TranslatedLine` in `packages/rentl-schemas/src/rentl_schemas/io.py`

## Template Variables

Allowed variables for translate phase (from `templates.py`):
- `game_name`, `game_synopsis` (root layer)
- `source_lang`, `target_lang` (phase layer)
- `scene_id`, `line_count`, `source_lines`, `scene_summary`, `pretranslation_notes`, `glossary_terms` (agent layer)
