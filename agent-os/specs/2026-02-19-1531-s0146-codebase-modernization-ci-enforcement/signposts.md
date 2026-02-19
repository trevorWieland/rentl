# Signposts

- **Task:** Task 2 (audit round 1)
- **Status:** unresolved
- **Problem:** The dataclass-to-Pydantic migration left multiple schema fields as raw annotations instead of `Field(..., description=...)`.
- **Evidence:** `ProviderCapabilities` uses raw fields (`name: str`, `is_openrouter: bool`, etc.) at `packages/rentl-llm/src/rentl_llm/providers.py:28`, `packages/rentl-llm/src/rentl_llm/providers.py:29`, `packages/rentl-llm/src/rentl_llm/providers.py:30`, and `packages/rentl-llm/src/rentl_llm/providers.py:31`.
- **Evidence:** Additional migrated models also use raw schema annotations, including `ProjectContext` (`packages/rentl-agents/src/rentl_agents/tools/game_info.py:19`), `_AgentCacheEntry` (`packages/rentl-agents/src/rentl_agents/factory.py:108`), `PromptLayerRegistry` (`packages/rentl-agents/src/rentl_agents/layers.py:64`), `PromptComposer` (`packages/rentl-agents/src/rentl_agents/layers.py:467`), `TemplateContext` (`packages/rentl-agents/src/rentl_agents/templates.py:274`), `AgentPoolBundle` (`packages/rentl-agents/src/rentl_agents/wiring.py:1107`), and `_AgentProfileSpec` (`packages/rentl-agents/src/rentl_agents/wiring.py:1117`).
- **Impact:** This violates `pydantic-only-schemas` and `strict-typing-enforcement` and can be repeated in later dataclass migration tasks if not corrected now.
- **Solution:** For each migrated schema field, replace raw annotations with `Field` declarations that include clear `description` metadata and validators where constraints are known.
