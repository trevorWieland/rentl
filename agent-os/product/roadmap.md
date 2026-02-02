# rentl Roadmap: From Playable to Professional-Grade

---

## v0.1: Playable Patch
**User Value:** "I can run a translation and get a playable patch"

**Primary Milestone:** End-to-end translation pipeline that produces a playable v1 translation in hours, not days.

**Key Differentiator:** First agentic localization pipeline that combines context intelligence, phase-based orchestration, and strict schemas—all with BYOK model support.

**Scope:**
- Complete 5-phase pipeline (ingest → [context → pretranslation (source text analysis) → translate → QA → edit] → export)
- One agent per phase (minimal but complete)
- CLI-first workflow (interactive setup → config → batch run)
- CSV/JSONL/TXT format support
- BYOK OpenAI-compatible endpoint configuration
- Basic QA checks + schema validation
- Progress observability by phase/line/scene
- Run-level progress events in progress streams (run_started/run_completed/run_failed)
- Export patch output
- Functional onboarding (you can get it working)
- Standards review: lock in declarative agent configuration and conventions

**Spec List (Expanded):**
- ✅ (01) Schema Definitions & Validation — Define strict Pydantic schemas for configs, inputs, outputs, and artifacts so the pipeline is deterministic and debuggable. **Depends on:** None.
- ✅ (02) Progress Semantics & Tracking — Establish progress invariants and summaries so phases can report trustworthy status and completion. **Depends on:** 01.
- ✅ (03) Import Adapter: CSV/JSONL/TXT — Normalize input data into canonical `SourceLine` records with schema validation. **Depends on:** 01.
- ✅ (04) Export Adapter: CSV/JSONL/TXT — Emit patch-ready output formats with audit hooks and schema validation. **Depends on:** 01, 03.
- ✅ (05) Run Persistence & Artifact Store Protocols — Define storage interfaces for run state, JSONL artifacts, and logs to enable durable runs and audits. **Depends on:** 01, 02.
- ✅ (06) Log/Event Taxonomy & Sink Protocols — Standardize run/phase event names and payloads for observability and status tooling. **Depends on:** 01, 02, 05.
- ✅ (07) Pipeline Orchestrator Core — Orchestrate flexible phase execution with dependency gating, deterministic merges, and staleness tracking; define when phase outputs are persisted as artifacts. **Depends on:** 01, 02, 05, 06.
- ✅ (08) Phase Execution & Sharding Config — Add per-phase execution strategies (full/scene/route) and concurrency controls. **Depends on:** 01, 07.
- ✅ (09) Phase History & Staleness Rules — Capture phase revisions and invalidate downstream outputs when upstream changes. **Depends on:** 01, 02, 07.
- ✅ (10) Phase Result Summaries & Metrics — Capture post-phase stats (glossary counts, QA totals, annotation coverage) for quality signals. **Depends on:** 01, 02, 07.
- ✅ (11) CLI Workflow & Phase Selection — Provide CLI commands to run a full plan or a single phase with clear status output; wire storage adapters into CLI runs. **Depends on:** 02, 07, 10.
- ✅ (12) BYOK Config & Endpoint Validation — Validate model endpoints and keys to avoid unsafe or unusable runs. **Depends on:** 01.
- ✅ (13) BYOK Runtime Integration — Implement OpenAI-compatible runtime clients (pydantic-ai) with retries/backoff. **Depends on:** 12.
- ✅ (14) Agent Runtime Scaffold (pydantic-ai) — Establish agent harness, prompts, and tool plumbing for phase agents. **Depends on:** 01, 12, 13.
- ✅ (15) Initial Phase Agent: Context — Scene summarizer agent with TOML profile, 3-layer prompts, and strict validation. Validated with real game data. **Depends on:** 14.
- ✅ (16) Initial Phase Agent: Pretranslation — Idiom Labeler agent that identifies idiomatic expressions, puns, wordplay, and culturally-specific phrases. Outputs `IdiomAnnotationList` with structured annotations. Validated with real LLM. **Depends on:** 14, 15.
- ✅ (17) Initial Phase Agent: Translate — Create our main translation agent, utilizing simple direct translation. This should take in context and pretranslation data, and output translated lines. Future translation agents would involve extra features like selective usage of other MTL models as tool calls. **Depends on:** 14, 15, 16.
- ✅ (18) Initial QA Checks (Deterministic) — Create deterministic and automated checks for formatting and completeness to enforce guardrails. **Depends on:** 01, 17.
- ✅ (19) Initial Phase Agent: QA — Create an initial agent to act in the QA phase. Candidates include (but are not limited to): inaccurate translation detection, style-guide adherence critic, incorrect pronoun usage detection, etc. **Depends on:** 14, 18.
- (20) Initial Phase Agent: Edit — Create our main editor agent, which will take in translated lines and apply targeted fixes based on QA findings for iterative improvements. Future editor agents would involve extra features like flagging a line for full retranslation, or using tools for more complex fixes. **Depends on:** 14, 17, 19.
- (21) Observability Surface (CLI Status Viewer) — Display live phase status and completion summaries for trust and clarity. **Depends on:** 02, 06, 10, 11.
- (22) Functional Onboarding — Guide users to a first successful run with defaults and validation. **Depends on:** 11, 13, 15–20.
- ✅ (23) Unit Test Coverage Gate (>80%) — Enforce unit test coverage threshold across core and CLI packages. **Depends on:** 01–13.
- ✅ (24) Integration Test Suite — Validate CLI workflows and runtime wiring across storage and BYOK endpoints. **Depends on:** 11, 12, 13, 23.
- (25) Quality Test Suite — Real-LLM smoke tests for runtime and agent behaviors. **Depends on:** 14, 15–20, 23.
- (25a) Standards Review: Declarative Agent Config — Lock in agent configuration conventions and documentation. **Depends on:** 14–16.
- (25b) End-to-End Logging & Error Surfacing — Ensure full logging coverage and raise actionable errors instead of silent failures. **Depends on:** 06, 07, 14–16.

**Success Criteria:**
- Produces higher-quality output than simple MTL
- End-to-end pipeline runs deterministically
- Users can complete a full project without expert intervention

---

## v0.2: Quality Leap
**User Value:** "I can run a translation and get a decent patch, with the same effort"

**Primary Milestone:** Translation quality jumps from "playable but rough" to "genuinely decent" through multi-agent teams per phase.

**Key Differentiator:** Each phase becomes a cohesive "team" of agents working together—smarter context analysis, more sophisticated translation, richer QA—rather than a single sample agent.

**Scope:**
- Multiple agents per phase (tuned based on v0.1 experience)
- Multi-agent orchestration with priority ordering and agent dependencies
- Context team: scene summarization + route summarizer + batch summarizer + character consistency
- Pretranslation team: idiom detector + reference finder + cultural note generator
- Translation team: multiple translators with different approaches (literal → liberal) + consensus selection
- QA team: style checker + consistency validator + cultural appropriateness reviewer
- Edit team: smart retranslation + pattern-based fixes + style alignment
- Agent hooks for pre/post LLM processing
- Richer QA checks (beyond basic style)
- Enhanced QA reporting with granular issue categorization
- Improved agent iteration visibility and control
- Functional onboarding refinements

**Spec List (Expanded):**
- (26) Agent Roster & Per-Phase Composition — Let users configure which agents run in a phase and in what mix. **Depends on:** 14, 15–20.
- (27) Agent Pool Scheduling & Queueing — Provide async scheduling, backpressure, and sharding for multi-agent teams. **Depends on:** 07, 08, 26.
- (28) Per-Agent Telemetry & Progress — Show which agents are running, finished, or blocked within a phase. **Depends on:** 06, 21, 26, 27.
- (29) HITL Review & Manual Artifacts — Enable pause/review/resume with human edits without full resets. **Depends on:** 05, 07, 27.
- (30) Deterministic Merge Policies & Conflict Resolution — Add configurable resolution rules when multiple agents overlap. **Depends on:** 07, 26.
- (31) Incremental Rerun & Diffing — Rerun only impacted shards to reduce cost and iteration time. **Depends on:** 07, 08, 09, 27.
- (37) Multi-Agent Orchestration — Execute multiple agents per phase with priority ordering and depends_on relationships; route summarizer runs after scene summarizer. **Depends on:** 15, 26, 27.
- (38) Agent Hooks — Pre/post LLM generation callbacks for custom processing, validation, or logging. **Depends on:** 15.
- (39) BatchSummarizer Agent — Context agent for content without scene boundaries; processes arbitrary line batches. **Depends on:** 15, 26.
- (40) RouteSummarizer Agent — Context agent for route-level summaries; depends on scene summaries. **Depends on:** 15, 37.
- (41) User-Configurable Agent Output Schemas — Allow users to define custom agent output schemas via TOML or JSON Schema without writing Python code; supports dynamic schema generation and validation. **Depends on:** 14, 26.

**Success Criteria:**
- First-pass translations are noticeably higher quality than v0.1
- QA catches issues that v0.1 missed
- Translation quality feels "decent" rather than "playable but rough"

---

## v0.3: Scale & Ecosystem
**User Value:** "I can run a translation and get multiple decent patches, and it works for my game out of the box (for popular engines)"

**Primary Milestone:** Multi-language support and game engine integration unlock localization at scale.

**Key Differentiator:** One core context setup translates into N languages, and your favorite game engine works out of the box—no custom schema wrangling.

**Scope:**
- Multi-language batch orchestration (run N languages in parallel)
- Language-specific profiles and settings
- Cost controls and token usage tracking across languages
- Adapter interfaces framework
- Engine-specific adapters: RPG Maker, Ren'Py, Kirikiri
- Engine-specific schemas and import/export formats
- Batch management for large multi-language projects
- Multi-language progress tracking and reporting
- Functional onboarding refinements

**Spec List (Expanded):**
- (32) Multi-Language Batch Orchestration — Run multiple target languages in parallel with shared context. **Depends on:** 07, 08, 26, 27.
- (33) Adapter Interface Framework — Standardize adapter contracts for engines and storage backends (e.g., PostgreSQL storage adapters). **Depends on:** 01, 05.
- (34) Engine-Specific Adapters — Provide out-of-the-box adapters for popular engines. **Depends on:** 33.

**Success Criteria:**
- Users can translate one script into 3+ languages in one workflow
- RPG Maker, Ren'Py, or Kirikiri projects work out of the box
- Multi-language runs complete predictably with clear cost visibility

---

## v0.4: UX Polish
**User Value:** "I can run a translation and get multiple decent patches, and it works for my game out of the box (for popular engines), all from a convenient and nice TUI"

**Primary Milestone:** Complete TUI makes the entire workflow accessible without CLI mastery.

**Key Differentiator:** From setup to shipping, everything is doable from a polished, intuitive interface—no more terminal command memorization.

**Scope:**
- Complete TUI surface (beyond read-only status viewer)
- Interactive setup wizard (guided configuration, context input, model selection)
- Real-time progress monitoring with visual phase tracking
- QA review interface (view flagged lines, add reviewer notes inline)
- Edit workflow UI (triage issues, trigger edit cycles, preview fixes)
- Multi-language batch management UI
- Project and configuration management screens
- Visual dashboards for QA reporting and iteration analytics
- Settings and preferences interface
- Functional onboarding refinements
- Async usage audit: Refactor CLI configuration loading to be fully async


**Spec List (Expanded):**
- (35) Full TUI Workflow — Deliver a complete TUI for setup, progress, QA review, and edits. **Depends on:** 21, 27–29.

**Success Criteria:**
- Users can complete end-to-end workflows using only the TUI
- Non-technical users can run multi-language batches without CLI knowledge
- TUI feels polished and intuitive (not just functional)

---

## v1.0: Professional-Grade Tooling
**User Value:** "This is professional-grade tooling"

**Primary Milestone:** rentl reaches feature parity with enterprise CAT tools while maintaining the agility and accessibility that define it.

**Key Differentiator:** The combination of agentic automation, professional-grade reliability, rapid iteration, and delightful onboarding makes rentl a viable alternative to enterprise CAT stacks for small teams and a serious upgrade for fan translators.

**Scope:**
- **CAT-grade feature parity:**
  - Translation memory (TM) with fuzzy matching and reuse
  - Glossary/term locking with enforcement across all translation passes
  - Comprehensive QA suites (terminology, consistency, formatting, completeness)
  - Advanced reporting dashboards with iteration analytics
- **Rapid hotfix loop:**
  - Issue triage workflow (automated issue detection → human review → fix routing)
  - Editor agent applies fixes consistently across similar lines
  - Patch generation within minutes for targeted fixes
- **Reliability and stability:**
  - 99%+ end-to-end pipeline success rate
  - Strong stability guarantees for schemas and CLI
  - Clear deprecation paths and migration guides
  - Comprehensive error recovery and rollback
- **Delightful onboarding:**
  - Guided setup wizard with best-practice templates
  - Contextual help and documentation in the TUI
  - Project templates for different game types (visual novels, RPGs, etc.)
  - Partner-studio shared configs and templates
- **Operational maturity:**
  - Benchmarking framework with quality rubrics (accuracy, style fidelity, consistency)
  - Example/benchmark repository with real-game demos
  - Contributor-friendly architecture and documentation

**Spec List (Expanded):**
- (36) CAT-Grade Features — Add TM, glossary enforcement, advanced QA suites, and reporting for v1.0 parity. **Depends on:** 26–31.

**Success Criteria:**
- Feature parity with core CAT tool capabilities (TM, glossaries, QA suites, reporting)
- Rapid hotfix loop works reliably (issue → fix → patch in <10 minutes)
- v1.0 experience feels professional, reliable, and delightful
- Small pro teams can adopt rentl as their primary localization pipeline
- 100+ GitHub stars (directional community signal)

---

## Version Identity Summary

| Version | User Promise | Primary Leap |
|---------|--------------|--------------|
| **v0.1** | "Playable patch" | End-to-end pipeline works |
| **v0.2** | "Decent quality" | Multi-agent teams per phase |
| **v0.3** | "Scale & ecosystem" | Multi-language + engine adapters |
| **v0.4** | "Great UX" | Complete TUI workflow |
| **v1.0** | "Professional-grade" | CAT parity + reliability + polish |

---

## Post-v1.0 Future Directions (Out of Scope)

- Expanded adapter ecosystem (more engines, deeper integration)
- Hosted service layer with team collaboration features
- Advanced agent orchestration and auto-tuning
- Community marketplace for agent configurations and templates
- Enterprise features (SSO, audit logs, advanced permissions)
- Docker Compose support for collaborative/production deployments with hosted alternatives (PostgreSQL, hosted vector DB, etc.)
