# RENTL v1.0 TODO LIST

This document tracks all tasks required to reach v1.0 of the Rentl translation pipeline.

**Target**: Complete core translation pipeline with Context → Translate → Edit phases
**Current Status**: ~60% complete (CLI UX/HITL and testing still needed)
**Estimated Remaining Work**: 1,500-2,500 lines of code

---

## ⚠️ ARCHITECTURE REFACTOR REQUIRED

**Status**: Refactor complete for Context/Translator/Editor; remaining work focuses on CLI HITL UX, stats, and testing.

See `AGENTS.md` for complete architecture documentation.

### Architecture Refactor Tasks

- [x] **1. Update ProjectContext with locking and conflict detection** (~300-400 LOC)
  - [x] Add entity-level locks in `libs/core/src/rentl_core/context/project.py`
    - [x] `_scene_locks: dict[str, asyncio.Lock]` - Per-scene locks
    - [x] `_character_locks: dict[str, asyncio.Lock]` - Per-character locks
    - [x] `_location_locks: dict[str, asyncio.Lock]` - Per-location locks
    - [x] `_glossary_lock: asyncio.Lock` - Single glossary lock
  - [x] Add conflict tracking: `_recent_updates: dict[tuple[str, str, str], float]`
  - [x] Implement update methods with feedback-providing locks:
    - [x] `async update_scene_summary(scene_id, summary, origin, conflict_threshold=30)` - Returns success or conflict message
    - [x] `async update_character_bio(char_id, bio, origin, conflict_threshold=30)` - With conflict detection
    - [x] `async update_location_description(loc_id, desc, origin, conflict_threshold=30)` - With conflict detection
    - [x] Similar methods for all updateable fields
  - [x] Implement write-through persistence (immediate file writes after updates)

- [ ] **2. Create comprehensive CRUD tools** (~500-600 LOC)
  - [x] Create `libs/agents/src/rentl_agents/tools/scene.py`
    - [ ] `read_scene(scene_id, runtime)` - Get scene metadata + transcript (current: read_scene_overview)
    - [x] `update_scene_summary(scene_id, summary, runtime)` - Calls ProjectContext.update_scene_summary
    - [x] `update_scene_tags(scene_id, tags, runtime)` - With conflict detection
    - [x] `update_scene_characters(scene_id, char_ids, runtime)` - With conflict detection
    - [x] `update_scene_locations(scene_id, loc_ids, runtime)` - With conflict detection
  - [x] Create `libs/agents/src/rentl_agents/tools/character.py`
    - [x] `read_character(char_id, runtime)` - Get character metadata
    - [x] `update_character_name(char_id, name_tgt, runtime)` - With conflict detection
    - [x] `update_character_pronouns(char_id, pronouns, runtime)` - With conflict detection
    - [x] `update_character_bio(char_id, bio, runtime)` - With conflict detection
    - [ ] `add_character(char_id, ..., runtime)` - Create new character
  - [x] Create `libs/agents/src/rentl_agents/tools/location.py`
    - [x] `read_location(loc_id, runtime)` - Get location metadata
    - [x] `update_location_name(loc_id, name_tgt, runtime)` - With conflict detection
    - [x] `update_location_description(loc_id, desc, runtime)` - With conflict detection
    - [ ] `add_location(loc_id, ..., runtime)` - Create new location
  - [x] Create `libs/agents/src/rentl_agents/tools/glossary.py`
    - [x] `search_glossary(term, runtime)` - Find matching entries
    - [ ] `read_glossary_entry(term_src, runtime)` - Get specific entry
    - [x] `add_glossary_entry(term_src, term_tgt, notes, runtime)` - Create entry
    - [x] `update_glossary_entry(term_src, term_tgt, notes, runtime)` - With conflict detection
    - [ ] `delete_glossary_entry(term_src, runtime)` - Remove entry
  - [ ] Create `libs/agents/src/rentl_agents/tools/context_docs.py`
    - [ ] `list_context_docs(runtime)` - List available documents
    - [ ] `read_context_doc(filename, runtime)` - Get document contents (read-only)

- [ ] **3. Create stats tools for top-level agents** (~200-300 LOC)
  - [x] Create `libs/agents/src/rentl_agents/tools/stats.py`
  - [x] `get_context_status(runtime)` - Returns aggregate completion stats (scenes, characters, locations, etc.)
  - [x] `get_scene_completion(scene_id, runtime)` - Returns detailed completion for specific scene
  - [ ] `get_character_completion(char_id, runtime)` - Returns detailed completion for specific character
  - [x] `get_translation_progress(scene_id, runtime)` - Returns translation status for scene
  - [ ] `get_route_progress(route_id, runtime)` - Returns translation/QA progress for route

- [ ] **4. Refactor existing subagents to use `create_agent` + `CompiledSubAgent`** (~800-1000 LOC to modify)
  - [x] Refactor `scene_detailer.py`
    - [x] Change from `create_deep_agent` to `create_agent`
    - [x] Remove `middleware=[]` parameter
    - [x] Add `ContextInjectionMiddleware` class that sets `runtime.context.project_context`
    - [x] Wrap in `CompiledSubAgent(name="scene-detailer", description="...", runnable=graph)`
    - [x] Change factory signature: `create_scene_detailer_subagent(context: ProjectContext) -> CompiledSubAgent`
    - [x] Update tools to use new CRUD tools from step 2
  - [x] Refactor `character_detailer.py` - Same pattern as scene_detailer
  - [x] Refactor `location_detailer.py` - Same pattern as scene_detailer
  - [x] Refactor `glossary_curator.py` - Same pattern as scene_detailer
  - [x] Refactor `route_detailer.py` - Same pattern as scene_detailer
  - [x] Refactor `translate_scene.py` - Same pattern as scene_detailer

- [ ] **5. Create Context Builder top-level agent** (~400-500 LOC)
  - [ ] Create `libs/pipelines/src/rentl_pipelines/agents/context_builder.py`
  - [x] Implement `async create_context_builder_agent(project_path: Path) -> Agent`
  - [x] Load shared `ProjectContext` once: `context = await load_project_context(project_path)`
  - [x] Create all detailer subagents passing shared context: `create_scene_detailer_subagent(context)`
  - [x] Create stats tools for decision making
  - [x] Create `ContextMiddleware` class that injects context into `runtime.context.project_context`
  - [x] Use `create_deep_agent` with stats tools, subagents, middleware, interrupt_on, checkpointer
  - [x] Add system prompt for intelligent coordination
  - [x] Configure `interrupt_on` for all update tools (provenance-based HITL)
  - [x] Add `MemorySaver` checkpointer for HITL support

- [ ] **6. Create Translator top-level agent** (~300-400 LOC)
  - [ ] Create `libs/pipelines/src/rentl_pipelines/agents/translator.py`
  - [x] Implement `async create_translator_agent(project_path: Path) -> Agent`
  - [x] Load shared `ProjectContext` once
  - [x] Create translate_scene subagent passing shared context
  - [x] Create translation progress tools
  - [x] Create `ContextMiddleware` for runtime injection
  - [x] Use `create_deep_agent` with progress tools, subagents, middleware, interrupt_on, checkpointer
  - [x] Add system prompt for translation workflow coordination
  - [x] Configure `interrupt_on` for HITL
  - [x] Add checkpointer support

- [ ] **7. Update CLI commands to use top-level agents** (~200-300 LOC)
  - [x] Update `apps/cli/src/rentl_cli/commands/run.py`
  - [x] Change `context()` command to invoke Context Builder agent
  - [x] Change `translate()` command to invoke Translator agent
  - [x] Change `edit()` command to invoke Editor pipeline
  - [ ] Add HITL interrupt handling in CLI (display approval requests, get user input)
  - [ ] Add thread_id management for checkpointer persistence
  - [ ] Update result display to show agent decisions and stats (verbosity tiers)
  - [x] Add `reset-example` for repeatability

---

## 🚨 CRITICAL PATH (Must Have for v1.0)

These tasks are essential for a functional v1.0 release and should be completed in roughly this order:

### 1. Data Model Enhancements
- [x] Add provenance tracking (`*_origin` fields) to all data models in `libs/core/model/`
  - [x] Add to CharacterMetadata
  - [x] Add to LocationMetadata
  - [x] Add to SceneMetadata
  - [x] Add to RouteMetadata
  - [x] Add to GlossaryEntry
  - [x] Add to TranslatedLine
  - [x] Add to GameMetadata
  - [x] Add to SourceLineMeta
  - [x] Add mandatory validation (Pydantic validators)
  - [x] Update all tiny_vn example files with origin fields
  - [x] Fix linting (Google-style docstrings, TRY003 compliance)
  - [x] Pass all type checking
- [x] Implement translation output writer in `libs/core/io/writer.py`
  - [x] `write_translation()` function
  - [x] `write_qa_report()` function
  - [x] Async file operations with anyio

### 2. Context Builder Subagents
- [x] Create `scene_detailer` subagent (~200-300 LOC)
  - [x] Implement in `libs/agents/src/rentl_agents/subagents/scene_detailer.py`
  - [x] Add scene metadata tools (summary, tags, characters, locations)
  - [x] Integrate with DeepAgents framework
  - [x] Update CLI commands (`detail-scene`, `detail-mvp`)
- [x] Create `character_detailer` subagent (~210 LOC)
  - [x] Implement in `libs/agents/src/rentl_agents/subagents/character_detailer.py`
  - [x] Add `read_character()` tool
  - [x] Add `update_character_name_tgt()`, `update_character_pronouns()`, `update_character_notes()` tools with HITL
  - [x] Integrate with DeepAgents framework
  - [x] Add ProjectContext methods and `_write_characters()`
- [x] Create `location_detailer` subagent (~190 LOC)
  - [x] Implement in `libs/agents/src/rentl_agents/subagents/location_detailer.py`
  - [x] Add `read_location()` tool
  - [x] Add `update_location_name_tgt()`, `update_location_description()` tools with HITL
  - [x] Integrate with DeepAgents framework
  - [x] Add ProjectContext methods and `_write_locations()`
- [x] Create `glossary_curator` subagent (~200 LOC)
  - [x] Implement in `libs/agents/src/rentl_agents/subagents/glossary_curator.py`
  - [x] Add `search_glossary()` tool
  - [x] Add `add_glossary_entry()` tool with HITL
  - [x] Add `update_glossary_entry()` tool with HITL
  - [x] Integrate with DeepAgents framework
  - [x] Add ProjectContext methods and `_write_glossary()`
- [x] Create `route_detailer` subagent (~185 LOC)
  - [x] Implement in `libs/agents/src/rentl_agents/subagents/route_detailer.py`
  - [x] Add `read_route()` tool
  - [x] Add `update_route_synopsis()`, `update_route_characters()` tools with HITL
  - [x] Integrate with DeepAgents framework
  - [x] Add ProjectContext methods and `_write_routes()`

### 3. Translator Subagent (HIGHEST PRIORITY)
- [x] Add MTL backend configuration (~50-75 LOC)
  - [x] Update `libs/core/src/rentl_core/config/settings.py` with MTL env vars (MTL_URL, MTL_API_KEY, MTL_MODEL)
  - [x] Create `libs/agents/src/rentl_agents/backends/mtl.py` - OpenAI-compatible MTL client
- [x] Create translation tools (~100-150 LOC)
  - [x] Create `libs/agents/src/rentl_agents/tools/translation.py`
  - [x] Add `mtl_translate()` tool - Calls specialized MTL model (e.g., Sugoi-14B-Ultra)
  - [x] Add `write_translation()` tool with HITL integration
- [x] Implement `scene_translator` subagent (~350-400 LOC)
  - [x] Update `libs/agents/src/rentl_agents/graph/engine.py` with translate_scene function
  - [x] Dual translation approach: direct LLM translation OR mtl_translate() tool
  - [x] Context-aware translation using glossary/character data
  - [x] Line-by-line translation with metadata preservation
  - [x] Speaker identification and consistency
  - [x] Choice option handling
  - [x] Dynamic decision-making between translation approaches

### 4. Editor/QA Subagents
- [x] Implement `scene_style_checker` subagent (~300-400 LOC)
  - [x] Update `libs/agents/src/rentl_agents/subagents/style_checks.py`
  - [x] Check line length constraints (UI settings)
  - [x] Check style guide compliance
  - [x] Add `record_style_check()` tool
- [x] Implement `scene_consistency_checker` subagent (~300-400 LOC)
  - [x] Update `libs/agents/src/rentl_agents/subagents/consistency_checks.py`
  - [x] Cross-scene terminology validation
  - [x] Character pronoun consistency
  - [x] Glossary term usage validation
  - [x] Add `record_consistency_check()` tool
- [x] Implement `scene_translation_reviewer` subagent (~300-400 LOC)
  - [x] Create new file in `libs/agents/src/rentl_agents/subagents/`
  - [x] Translation quality assessment
  - [x] Faithfulness to source
  - [x] Natural English flow
  - [x] Add `record_translation_review()` tool

### 5. HITL Approval System
- [x] Build HITL approval framework (~200-300 LOC)
  - [x] Create `libs/agents/src/rentl_agents/hitl/approval.py`
  - [x] Provenance checking logic
  - [x] Approval policies (permissive/standard/strict)
  - [x] Human data protection
  - [x] Approval request formatting
  - [x] Integration with all update/add tools

### 6. Pipeline Orchestration
- [x] Create full Context Builder pipeline (~150-200 LOC)
  - [x] Update `libs/pipelines/src/rentl_pipelines/flows/context_builder.py`
  - [x] Orchestrate all detailer subagents
  - [x] Parallel execution where possible
  - [x] Progress reporting
- [x] Create Translator pipeline (~150-200 LOC)
  - [x] Create `libs/pipelines/src/rentl_pipelines/flows/translator.py`
  - [x] Scene-by-scene translation
  - [x] Context loading and passing
  - [x] Output persistence
- [x] Create Editor pipeline (~150-200 LOC)
  - [x] Create `libs/pipelines/src/rentl_pipelines/flows/editor.py`
  - [x] Run all QA checks
  - [x] Generate QA reports
  - [x] Aggregate results

### 7. CLI Commands
- [ ] Create `rentl init` command (~50 LOC)
  - [ ] Add to `apps/cli/src/rentl_cli/commands/`
  - [ ] Invoke Copier template
  - [ ] Project structure validation
- [ ] Create `rentl context` command (~50 LOC)
  - [x] Run Context Builder pipeline
  - [ ] Progress display
  - [ ] Error handling
- [ ] Create `rentl translate` command (~50 LOC)
  - [x] Run Translator pipeline
  - [ ] Batch processing options
  - [ ] Resume capability
- [ ] Create `rentl edit` command (~50 LOC)
  - [x] Run Editor pipeline
  - [ ] Report generation
  - [ ] Fix suggestions
- [x] Create `rentl reset-example` command (~50 LOC)
  - [x] Reset tiny_vn example metadata to initial state
  - [x] Remove agent-generated fields (annotations with *_origin = "agent:*")
  - [x] Important for testing repeatability

### 8. Project Template
- [ ] Implement Copier template structure (~100 LOC)
  - [ ] Complete `libs/templates/src/rentl_templates/copier/`
  - [ ] Template variables in `copier.yml`
  - [ ] Directory structure templates
  - [ ] Default metadata files
  - [ ] Example content

---

## 📦 SUPPORTING TASKS (Important but not blocking)

### Error Handling & Robustness
- [ ] Add comprehensive error handling throughout
  - [ ] Retry logic for transient LLM failures
  - [ ] Graceful degradation
  - [ ] User-friendly error messages
  - [ ] Recovery mechanisms
- [ ] Add progress reporting callbacks
  - [ ] Scene-level progress
  - [ ] Pipeline-level progress
  - [ ] Time estimates
- [ ] CLI verbosity tiers
  - [ ] Default: high-level progress/stats + subagent task starts/finishes (no LLM dumps)
  - [ ] Verbose: add tool call summaries and failures
  - [ ] Debug/log: full trace to log file only (LLM reasoning/tokens kept out of stdout)
- [ ] Add pytest fixtures/utilities to reset tiny_vn baseline before/after integration tests for repeatability
- [ ] Stats/report helpers (structured progress for CLI/agents)

### Documentation
- [ ] Add Google-style docstrings to all public functions
- [ ] Update inline code comments where needed
- [ ] Create API documentation
- [ ] Add usage examples to README

### Testing (Can be done in parallel)
- [ ] Write unit tests for data models (~200 LOC)
  - [ ] Model validation tests
  - [ ] Provenance tracking tests
- [ ] Write unit tests for loaders (~150 LOC)
  - [ ] Async loader tests
  - [ ] Error case handling
- [ ] Write integration tests for subagents (~300 LOC)
  - [ ] Mock LLM responses
  - [ ] Tool execution tests
  - [ ] HITL approval tests
- [ ] Write E2E tests for pipelines (~200 LOC)
  - [ ] Full workflow tests
  - [ ] tiny_vn example validation

### Example Project Completion
- [ ] Complete tiny_vn translations
  - [ ] Generate English translations for all 4 scenes
  - [ ] Add QA reports
  - [ ] Add sample context documents
  - [ ] Demonstrate full workflow

---

## 🎯 IMPLEMENTATION ORDER

Recommended sequence for maximum efficiency:

**Phase 1: Foundation (Week 1)**
1. Add provenance tracking to models
2. Implement translation output writer
3. Build HITL approval framework

**Phase 2: Translation Core (Week 2)**
4. Implement scene_translator subagent
5. Create translator pipeline
6. Add `rentl translate` CLI command
7. Test with tiny_vn example

**Phase 3: Context Enhancement (Week 3)**
8. Implement all detailer subagents
9. Create context builder pipeline
10. Add `rentl context` CLI command

**Phase 4: Quality Assurance (Week 4)**
11. Implement all editor subagents
12. Create editor pipeline
13. Add `rentl edit` CLI command

**Phase 5: Polish & Testing (Week 5-6)**
14. Complete project template
15. Add `rentl init` command
16. Write comprehensive tests
17. Complete documentation
18. Finalize tiny_vn example

---

## 📊 PROGRESS METRICS

**Lines of Code**:
- Current: ~2,130 LOC
- Target: ~4,500-5,500 LOC
- Remaining: ~2,000-3,000 LOC

**Components**:
- [x] Data models (100% - provenance tracking complete with validation)
- [x] Async loaders (100%)
- [x] Basic CLI framework (100%)
- [x] Scene detailer (100%)
- [x] Context Builder subagents (100% - character, location, glossary, route detailers complete)
- [x] Translator subagent (100% - scene_translator complete)
- [x] HITL system (100% - provenance-based approval implemented)
- [x] Editor subagents (style/consistency/reviewer) (100%)
- [x] Full pipelines (context/translate/edit) (100%)
- [ ] Project template (5%)
- [ ] Tests (10% - unit coverage starting)

**Subagents Status** (9/9 core subagents implemented):
- [x] scene_detailer
- [x] character_detailer
- [x] location_detailer
- [x] glossary_curator
- [x] route_detailer
- [x] scene_translator
- [x] scene_style_checker
- [x] scene_consistency_checker
- [x] scene_translation_reviewer
- [ ] detect_references (v1.1 - deferred)
- [ ] detect_puns (v1.1 - deferred)

**CLI Commands** (5/6 implemented):
- [x] validate
- [x] detail-scene (development only)
- [x] context
- [x] translate
- [x] edit
- [ ] init

---

## 🚀 DEFINITION OF DONE for v1.0

A task is considered complete when:
1. Code is implemented and working
2. Unit tests pass (where applicable)
3. Integration with pipeline successful
4. CLI command can invoke it
5. tiny_vn example demonstrates it
6. Documentation updated

**v1.0 is complete when**:
- [ ] Can initialize a new project with `rentl init`
- [x] Can validate project structure with `rentl validate`
- [ ] Can enrich metadata with `rentl context` (with CLI HITL UX)
- [ ] Can translate scenes with `rentl translate` (with CLI HITL UX/resume)
- [ ] Can run QA checks with `rentl edit` (with report output)
- [ ] 90% test coverage of high-impact code.
- [ ] Documentation is complete

---

## 📝 NOTES

- Focus on translation pipeline first (it's the core value)
- HITL approval system is critical for user trust
- Provenance tracking enables safe human-AI collaboration
- Tests can be written in parallel by another developer
- Web UI is explicitly deferred to v1.3
- Keep MVP mindset: working pipeline > perfect code

**Resolved questions**:
1. **Translation approach**: Dual approach - subagents can translate directly OR call `mtl_translate()` tool for specialized translation models (e.g., Sugoi-14B-Ultra). MTL backend configured via env vars (MTL_URL, MTL_API_KEY, MTL_MODEL) using OpenAI-compatible interface.
2. **Parallel processing**: Determined dynamically by top-level DeepAgents orchestrator. The Translation agent decides which subagents to run, when, and whether to rerun based on output quality. Enables intelligent iterative workflows.
3. **Approval policies**: Defined in SCHEMAS.md - read_* (never approve), add_* (permissive/strict), update_* (standard checks provenance/strict always approves), delete_* (standard checks human authorship/strict always approves).
4. **Progress reporting**: Log-level based. Non-verbose mode logs subagent invocations only. Verbose mode (`--verbose`) shows detailed step logging. Future: Progress % for naive passes (not dynamic agent passes).

---

*Last Updated: 2025-11-22*
