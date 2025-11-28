# RENTL v1.0 TODO LIST

This document tracks all tasks required to reach v1.0 of the Rentl translation pipeline.

**Target**: Complete core translation pipeline with Context → Translate → Edit phases (Pretranslation in v1.1)
**Current Status**: ~75% complete (CLI UX/resume, retries/progress surface, and testing still needed)

**Direction update**: Top-level DeepAgents coordinators are being retired in favor of deterministic, phase-first pipelines that schedule LangChain subagents directly. HITL will rely on LangChain middleware + provenance-aware tools. UX will emphasize a Textual TUI (plus CLI) with per-phase dashboards and a HITL inbox.

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
- [x] Add queue-based execution with bounded concurrency and resumable thread IDs (HITL middleware + thread_id + SQLite checkpointer now wired)
- [x] Support modes: overwrite, gap-fill, new-only; per-scene/route targeting
- [x] Add retry/backoff and failure surfacing in pipelines (error collection + backoff added; progress callbacks wired)
- [ ] Surface status/resume/failure details to CLI/TUI (status command + resume UX)

### CLI UX (TUI later)
- [ ] Update CLI commands to expose status/resume + HITL decisions (thread_id wiring present; add status/resume command using checkpoints + progress callbacks)
- [ ] Onboarding/smoke test for model config; `status` command for phase stats
- [ ] Plan Textual TUI (phase dashboards, job queue, HITL inbox) after CLI parity

### Testing & fixtures
- [x] Unit/integration tests for pipelines with mocked LLMs and retry/error handling
- [x] HITL/resume persistence tests with SQLite checkpointer (interrupt/resume smoke)
- [x] Fixtures to reset a temp tiny_vn baseline per test (no mutations to real example)
- [x] QA output/report validation (editor report smoke test added)
- [x] Tiny_vn end-to-end smoke test with stubbed agents (context → translate → edit)

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
- [ ] Complete Copier template and wire `rentl init`
- [ ] Document/setup flow for non-technical users (keys/models, smoke test)
- [ ] Template variables in `copier.yml`
- [ ] Directory structure templates + default metadata files

---

## 📦 SUPPORTING TASKS

### Error Handling & Robustness
- [ ] Add comprehensive error handling throughout
  - [x] Retry logic for transient LLM failures (pipeline backoff wrappers)
  - [ ] Graceful degradation
  - [ ] User-friendly error messages
  - [ ] Recovery mechanisms
- [ ] Add progress reporting callbacks
  - [x] Scene-level progress (callbacks + CLI verbose printing)
  - [ ] Pipeline-level progress/state and resume UX
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

### Testing
- [ ] Write unit tests for data models
  - [ ] Model validation tests
  - [ ] Provenance tracking tests
- [ ] Write unit tests for loaders
  - [ ] Async loader tests
  - [ ] Error case handling
- [ ] Write integration tests for subagents
  - [ ] Mock LLM responses
  - [ ] Tool execution tests
  - [ ] HITL approval tests
- [ ] Write E2E tests for pipelines
  - [ ] Full workflow tests with real LLMs
  - [ ] agentevals-based testing
  - [ ] tiny_vn example validation

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
- [ ] Can initialize a new project using copier with `rentl init`
- [x] Can validate project structure with `rentl validate`
- [ ] Can enrich metadata with `rentl context` (with CLI HITL UX)
- [ ] Can translate scenes with `rentl translate` (with CLI HITL UX/resume)
- [ ] Can run QA checks with `rentl edit` (with report output)
- [ ] 90% test coverage.
- [ ] Documentation is complete
