# RENTL v1.0 TODO LIST

This document tracks all tasks required to reach v1.0 of the Rentl translation pipeline.

**Target**: Complete core translation pipeline with Context → Translate → Edit phases (Pretranslation in v1.1)
**Current Status**: ~60% complete (CLI UX, HITL polish, concurrency/queueing, and testing still needed)
**Estimated Remaining Work**: 1,500-2,500 lines of code

**Direction update (2025-03)**: Top-level DeepAgents coordinators are being retired in favor of deterministic, phase-first pipelines that schedule LangChain subagents directly. HITL will rely on LangChain middleware + provenance-aware tools. UX will emphasize a Textual TUI (plus CLI) with per-phase dashboards and a HITL inbox.

---

## Remaining Work (pipeline-first)

### Tools & stats
- [x] Core scene/character/location/glossary tools updated
  - [x] `read_scene(scene_id, runtime)` returns metadata + transcript
  - [x] `add_character(...)`
  - [x] `add_location(...)`
  - [x] `read_glossary_entry(term_src, runtime)`
  - [x] `delete_glossary_entry(term_src, runtime)`
  - [x] Context docs tools: `list_context_docs`, `read_context_doc` (centralized)
- [x] Stats coverage: `get_character_completion`, `get_route_progress`

### Phase pipelines & execution
- [ ] Polish deterministic runners (context/translate/edit) and add pretranslate when ready
- [ ] Add queue-based execution with bounded concurrency and resumable thread IDs (HITL pauses via LangChain middleware)
- [ ] Support modes: overwrite, gap-fill, new-only; per-scene/route targeting
- [ ] Add retry/backoff, failure surfacing, and progress/state APIs for CLI (TUI later)

### CLI UX (TUI later)
- [ ] Update CLI commands to call new runners (mode/target flags), expose status, and manage thread_id + HITL decisions
- [ ] Onboarding/smoke test for model config; `status` command for phase stats
- [ ] Plan Textual TUI (phase dashboards, job queue, HITL inbox) after CLI parity

### Testing & fixtures
- [ ] Unit/integration tests for pipelines with mocked LLMs and HITL decisions
- [ ] Fixtures to reset `examples/tiny_vn` baseline before/after runs
- [ ] QA output/report validation

### Template & onboarding
- [ ] Complete Copier template and wire `rentl init`
- [ ] Document/setup flow for non-technical users (keys/models, smoke test)

### Completed foundations (for reference)
- Data models with provenance; async loaders/writers
- HITL approval framework (provenance-aware tools)
- Subagents for context, translation, QA; translation tools and MTL backend
- Deterministic pipelines for context/translate/edit (non-queued)

### CLI commands
- [ ] `rentl init` (Copier wiring)
- [x] `rentl context` (needs richer progress display/error handling)
- [x] `rentl translate` (needs batch/resume options)
- [x] `rentl edit` (needs report generation/fix suggestions)
- [x] `rentl reset-example` (baseline now sparse)

### Project Template
- [ ] Implement Copier template structure
- [ ] Template variables in `copier.yml`
- [ ] Directory structure templates + default metadata files

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
2. **Parallel processing**: Pipelines are deterministic; add bounded concurrency/queues in code (no LLM planners). Reruns derive from on-disk state.
3. **Approval policies**: Defined in SCHEMAS.md - read_* (never approve), add_* (permissive/strict), update_* (standard checks provenance/strict always approves), delete_* (standard checks human authorship/strict always approves).
4. **Progress reporting**: Log-level based. Non-verbose mode logs pipeline/subagent invocations only. Verbose mode (`--verbose`) shows detailed step logging. Future: Progress % from state-derived queues.

---

*Last Updated: 2025-03-15*
