# RENTL v1.0 TODO LIST

This document tracks all tasks required to reach v1.0 of the Rentl translation pipeline.

**Target**: Complete core translation pipeline with Context → Translate → Edit phases
**Current Status**: ~40% complete (Context Builder subagents + Scene Translator complete)
**Estimated Remaining Work**: 2,000-3,000 lines of code

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
- [ ] Implement `scene_style_checker` subagent (~300-400 LOC)
  - [ ] Update `libs/agents/src/rentl_agents/subagents/style_checks.py`
  - [ ] Check line length constraints (42 chars)
  - [ ] Check style guide compliance
  - [ ] Add `record_style_check()` tool
- [ ] Implement `scene_consistency_checker` subagent (~300-400 LOC)
  - [ ] Update `libs/agents/src/rentl_agents/subagents/consistency_checks.py`
  - [ ] Cross-scene terminology validation
  - [ ] Character pronoun consistency
  - [ ] Glossary term usage validation
  - [ ] Add `record_consistency_check()` tool
- [ ] Implement `scene_translation_reviewer` subagent (~300-400 LOC)
  - [ ] Create new file in `libs/agents/src/rentl_agents/subagents/`
  - [ ] Translation quality assessment
  - [ ] Faithfulness to source
  - [ ] Natural English flow
  - [ ] Add `record_translation_review()` tool

### 5. HITL Approval System
- [x] Build HITL approval framework (~200-300 LOC)
  - [x] Create `libs/agents/src/rentl_agents/hitl/approval.py`
  - [x] Provenance checking logic
  - [x] Approval policies (permissive/standard/strict)
  - [x] Human data protection
  - [x] Approval request formatting
  - [x] Integration with all update/add tools

### 6. Pipeline Orchestration
- [ ] Create full Context Builder pipeline (~150-200 LOC)
  - [ ] Update `libs/pipelines/src/rentl_pipelines/flows/context_builder.py`
  - [ ] Orchestrate all detailer subagents
  - [ ] Parallel execution where possible
  - [ ] Progress reporting
- [ ] Create Translator pipeline (~150-200 LOC)
  - [ ] Create `libs/pipelines/src/rentl_pipelines/flows/translator.py`
  - [ ] Scene-by-scene translation
  - [ ] Context loading and passing
  - [ ] Output persistence
- [ ] Create Editor pipeline (~150-200 LOC)
  - [ ] Create `libs/pipelines/src/rentl_pipelines/flows/editor.py`
  - [ ] Run all QA checks
  - [ ] Generate QA reports
  - [ ] Aggregate results

### 7. CLI Commands
- [ ] Create `rentl init` command (~50 LOC)
  - [ ] Add to `apps/cli/src/rentl_cli/commands/`
  - [ ] Invoke Copier template
  - [ ] Project structure validation
- [ ] Create `rentl context` command (~50 LOC)
  - [ ] Run Context Builder pipeline
  - [ ] Progress display
  - [ ] Error handling
- [ ] Create `rentl translate` command (~50 LOC)
  - [ ] Run Translator pipeline
  - [ ] Batch processing options
  - [ ] Resume capability
- [ ] Create `rentl edit` command (~50 LOC)
  - [ ] Run Editor pipeline
  - [ ] Report generation
  - [ ] Fix suggestions
- [ ] Create `rentl reset-example` command (~50 LOC)
  - [ ] Reset tiny_vn example metadata to initial state
  - [ ] Remove agent-generated fields (annotations with *_origin = "agent:*")
  - [ ] Important for testing repeatability

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
- [ ] Editor subagents (0%)
- [ ] Full pipelines (10%)
- [ ] Project template (5%)
- [ ] Tests (0%)

**Subagents Status** (6/9 core subagents implemented):
- [x] scene_detailer
- [x] character_detailer
- [x] location_detailer
- [x] glossary_curator
- [x] route_detailer
- [x] scene_translator
- [ ] scene_style_checker
- [ ] scene_consistency_checker
- [ ] scene_translation_reviewer
- [ ] detect_references (v1.1 - deferred)
- [ ] detect_puns (v1.1 - deferred)

**CLI Commands** (2/6 implemented):
- [x] validate
- [x] detail-scene (development only)
- [ ] init
- [ ] context
- [ ] translate
- [ ] edit

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
- [ ] Can validate project structure with `rentl validate`
- [ ] Can enrich metadata with `rentl context`
- [ ] Can translate scenes with `rentl translate`
- [ ] Can run QA checks with `rentl edit`
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