# RENTL v1.0 TODO LIST

This document tracks all tasks required to reach v1.0 of the Rentl translation pipeline.

**Target**: Complete core translation pipeline with Context → Translate → Edit phases
**Current Status**: ~25% complete (MVP with scene summarization working)
**Estimated Remaining Work**: 3,000-4,000 lines of code

---

## 🚨 CRITICAL PATH (Must Have for v1.0)

These tasks are essential for a functional v1.0 release and should be completed in roughly this order:

### 1. Data Model Enhancements
- [ ] Add provenance tracking (`*_origin` fields) to all data models in `libs/core/model/`
  - [ ] Add to CharacterMetadata
  - [ ] Add to LocationMetadata
  - [ ] Add to SceneMetadata
  - [ ] Add to RouteMetadata
  - [ ] Add to GlossaryEntry
  - [ ] Add to TranslatedLine
- [ ] Implement translation output writer in `libs/core/io/writer.py`
  - [ ] `write_translation()` function
  - [ ] `write_qa_report()` function
  - [ ] Async file operations with anyio

### 2. Context Builder Subagents
- [ ] Create `character_detailer` subagent (~200-300 LOC)
  - [ ] Implement in `libs/agents/src/rentl_agents/subagents/character_detailer.py`
  - [ ] Add `read_character()` tool
  - [ ] Add `update_character()` tool with HITL
  - [ ] Integrate with DeepAgents framework
- [ ] Create `location_detailer` subagent (~200-300 LOC)
  - [ ] Implement in `libs/agents/src/rentl_agents/subagents/location_detailer.py`
  - [ ] Add `read_location()` tool
  - [ ] Add `update_location()` tool with HITL
- [ ] Create `glossary_detailer` subagent (~200-300 LOC)
  - [ ] Implement in `libs/agents/src/rentl_agents/subagents/glossary_curator.py`
  - [ ] Add `read_glossary()` tool with search
  - [ ] Add `add_glossary_entry()` tool with HITL
  - [ ] Add `update_glossary_entry()` tool with HITL
- [ ] Create `route_detailer` subagent (~200-300 LOC)
  - [ ] Implement in `libs/agents/src/rentl_agents/subagents/route_detailer.py`
  - [ ] Add `read_route()` tool
  - [ ] Add `update_route()` tool with HITL

### 3. Translator Subagent (HIGHEST PRIORITY)
- [ ] Implement `scene_translator` subagent (~400-500 LOC)
  - [ ] Update `libs/agents/src/rentl_agents/subagents/translate_scene.py`
  - [ ] Add `write_translation()` tool
  - [ ] Context-aware translation using glossary/character data
  - [ ] Line-by-line translation with metadata preservation
  - [ ] Speaker identification and consistency
  - [ ] Choice option handling

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
- [ ] Build HITL approval framework (~200-300 LOC)
  - [ ] Create `libs/agents/src/rentl_agents/hitl/approval.py`
  - [ ] Provenance checking logic
  - [ ] Approval policies (permissive/standard/strict)
  - [ ] Human data protection
  - [ ] Approval request formatting
  - [ ] Integration with all update/add tools

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
- Current: ~1,137 LOC
- Target: ~4,500-5,500 LOC
- Remaining: ~3,000-4,000 LOC

**Components**:
- [x] Data models (85% - missing provenance)
- [x] Async loaders (100%)
- [x] Basic CLI framework (100%)
- [x] Scene summarizer (100%)
- [ ] Translator subagent (0%)
- [ ] Editor subagents (0%)
- [ ] Detailer subagents (0%)
- [ ] HITL system (0%)
- [ ] Full pipelines (10%)
- [ ] Project template (5%)
- [ ] Tests (0%)

**Subagents Status** (1/11 implemented):
- [x] scene_detailer (summarizer)
- [ ] character_detailer
- [ ] location_detailer
- [ ] glossary_detailer
- [ ] route_detailer
- [ ] scene_translator
- [ ] scene_style_checker
- [ ] scene_consistency_checker
- [ ] scene_translation_reviewer
- [ ] detect_references (v1.1)
- [ ] detect_puns (v1.1)

**CLI Commands** (2/6 implemented):
- [x] validate
- [x] summarize-mvp (development only)
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
- [ ] tiny_vn has complete English translations
- [ ] All tests pass
- [ ] Documentation is complete

---

## 📝 NOTES

- Focus on translation pipeline first (it's the core value)
- HITL approval system is critical for user trust
- Provenance tracking enables safe human-AI collaboration
- Tests can be written in parallel by another developer
- Web UI is explicitly deferred to v1.3
- Keep MVP mindset: working pipeline > perfect code

**Questions to resolve**:
1. Which LLM model for translation? (GPT-4, Claude, etc.)
2. Batch size for parallel scene processing?
3. Default approval policies for different operations?
4. Progress reporting granularity?

---

*Last Updated: 2024-11-22*
*Generated for Rentl v1.0 development*