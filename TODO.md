# RENTL v1.0 TODO LIST

This document tracks all tasks required to reach v1.0 of the Rentl translation pipeline.

**Target**: Complete core translation pipeline with Context → Translate → Edit phases (Pretranslation in v1.1)
**Current Status**: ~80% complete (CLI UX/resume, retries/progress surface, and testing still needed)

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
- [x] Support modes: overwrite, gap-fill, new-only; per-scene targeting complete, route targeting/resume UX improved (CLI route filters added; route-level thread ids/snapshots deterministic with scope-aware resume)
- [x] Editor pipeline skips already QA'd or untranslated scenes based on mode (overwrite/gap-fill/new-only)
- [x] Skip transparency across phases (context/translate/edit) with reasons surfaced in CLI/report payloads
- [x] Add retry/backoff and failure surfacing in pipelines (error collection + backoff added; progress callbacks wired)
- [x] Surface status/resume/failure details to CLI/TUI (status now includes translation/editing %, route breakdown, thread id hints, per-entity failures, time/estimate)

### CLI UX (TUI later)
- [x] Add explicit resume flags for context/translate/edit and error when thread id missing
- [x] Resume convenience: `--resume-latest` to reuse latest checkpoint thread id for context/translate/edit
- [x] Update CLI commands to expose status/resume + HITL decisions (thread_id wiring present; status command added; richer resume UX improved)
- [x] Onboarding/smoke test for model config; `status` command for phase stats (status exists with public snapshot JSON + --public; onboarding added via doctor command)
- [ ] Plan Textual TUI (phase dashboards, job queue, HITL inbox) after CLI parity
- [x] Add `--no-checkpoint` toggle for quick local runs

### Testing & fixtures
- [x] Unit/integration tests for pipelines with mocked LLMs and retry/error handling
- [x] HITL/resume persistence tests with SQLite checkpointer (interrupt/resume smoke)
- [x] Fixtures to reset a temp tiny_vn baseline per test (no mutations to real example)
- [x] QA output/report validation (editor report smoke test added)
- [x] Tiny_vn end-to-end smoke test with stubbed agents (context → translate → edit)
- [x] HITL interrupt/resume integration test to validate middleware + runner loop
- [x] Basic model/loader validation tests (provenance requirements, missing/invalid files)
- [x] HITL interrupt formatting tests (action_requests parsing, decision normalization)
- [x] HITL decision flow integration test with mocked subagent/resume
- [x] Route filter integration tests for pipelines
- [x] HITL reject decision test to ensure decisions propagate
- [x] Source-language metadata preservation test
- [x] HITL tool provenance tests for approve/reject paths
- [x] Source-language write tests for context detailers with human-authored data (no overwrite)
- [x] Context pipeline end-to-end test with mocked LLMs (real flow on tiny_vn, HITL pause/resume, status snapshot)
- [x] Translator pipeline end-to-end test with mocked LLMs (real flow on tiny_vn, overwrite/gap-fill coverage, progress)
- [x] Editor pipeline end-to-end test with mocked LLMs (real flow on tiny_vn, report contents, route issue counts)
- [x] HITL approval/interrupt edge coverage (rentl_agents/hitl/approval.py, invoke.py)
- [x] Tool coverage across scene/character/location/glossary/route/qa/stats/translation (provenance, conflicts, delete)
- [x] ProjectContext persistence/conflict branches (routes/characters/locations/glossary delete, translation writer)
- [x] Loader error/empty-line coverage (JSON/JSONL parsing edges)
- [x] Backend stubs coverage (mtl prompt override/availability, graph/engine placeholders)

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
- [x] Add progress reporting callbacks
  - [x] Scene-level progress (callbacks + CLI verbose printing)
  - [x] Pipeline-level progress/state and resume UX
  - [x] Time estimates
- [x] CLI verbosity tiers
  - [x] Default: high-level progress/stats + subagent task starts/finishes (no LLM dumps)
  - [x] Verbose: add tool call summaries and failures
  - [x] Debug/log: full trace to log file only (LLM reasoning/tokens kept out of stdout)
- [x] Add pytest fixtures/utilities to reset tiny_vn baseline before/after integration tests for repeatability
- [x] Stats/report helpers (structured progress for CLI/agents)
- [x] Surface route issue counts and top issues in CLI/status snapshots
- [x] Add phase timestamp/thread-id hints in progress snapshots

### Documentation
- [ ] Add Google-style docstrings to all public functions
- [ ] Update inline code comments where needed
- [ ] Create API documentation
- [ ] Add usage examples to README

### Testing
- [x] Write unit tests for data models
  - [x] Model validation tests
  - [x] Provenance tracking tests
- [x] Write unit tests for loaders
  - [x] Async loader tests
  - [x] Error case handling
- [x] Write integration tests for subagents
  - [x] Mock LLM responses
  - [x] Tool execution tests
  - [x] HITL approval tests
- [x] Add live LLM test gate and helpers
  - [x] `llm_live` pytest marker + `RENTL_LLM_TESTS` env guard (require OPENAI_URL, OPENAI_API_KEY, LLM_MODEL)
  - [x] Shared helper to run subagents with MemorySaver + auto-approve decisions and return trajectories
  - [x] Makefile target `check-full` that runs `make check` + `pytest -m llm_live`
- [ ] Live agentevals coverage (per-subagent)
  - [ ] Scene detailer: trajectory match (superset) requires write_* tools; LLM judge for source-language summary/tags/locations
  - [ ] Character detailer: trajectory match uses write_* character tools; judge checks source-language notes + target names/pronouns
  - [ ] Location detailer: trajectory match uses write_* location tools; judge checks source-language descriptions
  - [ ] Route detailer: trajectory match uses write_* route tools; judge checks source-language synopses
  - [ ] Glossary curator: trajectory match uses add/update/delete glossary tools; judge checks source/target language fields
  - [ ] Translator: trajectory match ensures one write_translation per line (allow mtl_translate optionally); LLM judge for target language and non-copying
  - [ ] Style checker: trajectory match requires read_translations + record_style_check; judge encourages style-guide/UI usage
  - [ ] Consistency checker: trajectory match requires read_translations + record_consistency_check; judge checks consistency rationale
  - [ ] Translation reviewer: trajectory match requires read_translations + record_translation_review; judge checks fidelity/fluency notes
- [ ] Pipeline live smoke
  - [ ] Context pipeline with real LLM (concurrency=1, checkpoint_disabled) writes metadata to disk
  - [ ] Translator pipeline with real LLM (concurrency=1, checkpoint_disabled) writes translations to disk
  - [ ] Editor pipeline with real LLM (concurrency=1, checkpoint_disabled) writes QA checks/report to disk
  - [x] tiny_vn example validation

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
- [x] Can enrich metadata with `rentl context` (with CLI HITL UX)
- [x] Can translate scenes with `rentl translate` (with CLI HITL UX/resume)
- [x] Can run QA checks with `rentl edit` (with report output)
- [ ] 90% test coverage.
- [ ] Documentation is complete
