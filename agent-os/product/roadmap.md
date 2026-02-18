# rentl Roadmap: From Playable to Professional-Grade

---

## v0.1: Playable Patch
**User Value:** "I can run an Agentic Localization pipeline and get a playable patch"

**Primary Milestone:** End-to-end localization pipeline that produces a playable v1 patch in hours, not years.

**Key Differentiator:** First agentic localization pipeline that combines context intelligence, phase-based orchestration, and strict schemas—all with BYOK model support.

**Scope:**
- Complete 5-phase pipeline (ingest → [context → pretranslation → translate → QA → edit] → export)
- One agent per phase (minimal but complete)
- CLI-first workflow (init → config → batch run → export)
- Project bootstrap via template and sample data
- CSV/JSONL/TXT import and export adapters
- BYOK OpenAI-compatible endpoint support (OpenAI, OpenRouter, local)
- Deterministic QA checks + schema validation
- Progress observability by phase/line/scene with status viewer
- Run persistence and artifact storage
- Functional onboarding surfaces (docs + help + doctor)
- Standards review: declarative agent configuration and conventions
- Log redaction and error taxonomy enforcement
- Model default freshness (no presets with announced EOL)
- Release documentation (CHANGELOG, Getting Started, architecture, schema reference)

**Spec List (Expanded):**
- ✅ (s0.1.01) Schema Definitions & Validation — Define strict Pydantic schemas for configs, inputs, outputs, and artifacts so the pipeline is deterministic and debuggable. **Depends on:** None.
- ✅ (s0.1.02) Progress Semantics & Tracking — Establish progress invariants and summaries so phases can report trustworthy status and completion. **Depends on:** s0.1.01.
- ✅ (s0.1.03) Import Adapter: CSV/JSONL/TXT — Normalize input data into canonical `SourceLine` records with schema validation. **Depends on:** s0.1.01.
- ✅ (s0.1.04) Export Adapter: CSV/JSONL/TXT — Emit patch-ready output formats with audit hooks and schema validation. **Depends on:** s0.1.01, s0.1.03.
- ✅ (s0.1.05) Run Persistence & Artifact Store Protocols — Define storage interfaces for run state, JSONL artifacts, and logs to enable durable runs and audits. **Depends on:** s0.1.01, s0.1.02.
- ✅ (s0.1.06) Log/Event Taxonomy & Sink Protocols — Standardize run/phase event names and payloads for observability and status tooling. **Depends on:** s0.1.01, s0.1.02, s0.1.05.
- ✅ (s0.1.07) Pipeline Orchestrator Core — Orchestrate flexible phase execution with dependency gating, deterministic merges, and staleness tracking; define when phase outputs are persisted as artifacts. **Depends on:** s0.1.01, s0.1.02, s0.1.05, s0.1.06.
- ✅ (s0.1.08) Phase Execution & Sharding Config — Add per-phase execution strategies (full/scene/route) and concurrency controls. **Depends on:** s0.1.01, s0.1.07.
- ✅ (s0.1.09) Phase History & Staleness Rules — Capture phase revisions and invalidate downstream outputs when upstream changes. **Depends on:** s0.1.01, s0.1.02, s0.1.07.
- ✅ (s0.1.10) Phase Result Summaries & Metrics — Capture post-phase stats (glossary counts, QA totals, annotation coverage) for quality signals. **Depends on:** s0.1.01, s0.1.02, s0.1.07.
- ✅ (s0.1.11) CLI Workflow & Phase Selection — Provide CLI commands to run a full plan or a single phase with clear status output; wire storage adapters into CLI runs. **Depends on:** s0.1.02, s0.1.07, s0.1.10.
- ✅ (s0.1.12) BYOK Config & Endpoint Validation — Validate model endpoints and keys to avoid unsafe or unusable runs. **Depends on:** s0.1.01.
- ✅ (s0.1.13) BYOK Runtime Integration — Implement OpenAI-compatible runtime clients (pydantic-ai) with retries/backoff. **Depends on:** s0.1.12.
- ✅ (s0.1.14) Agent Runtime Scaffold (pydantic-ai) — Establish agent harness, prompts, and tool plumbing for phase agents. **Depends on:** s0.1.01, s0.1.12, s0.1.13.
- ✅ (s0.1.15) Initial Phase Agent: Context — Scene summarizer agent with TOML profile, 3-layer prompts, and strict validation. Validated with real game data. **Depends on:** s0.1.14.
- ✅ (s0.1.16) Initial Phase Agent: Pretranslation — Idiom Labeler agent that identifies idiomatic expressions, puns, wordplay, and culturally-specific phrases. Outputs `IdiomAnnotationList` with structured annotations. Validated with real LLM. **Depends on:** s0.1.14, s0.1.15.
- ✅ (s0.1.17) Initial Phase Agent: Translate — Create our main translation agent, utilizing simple direct translation. This should take in context and pretranslation data, and output translated lines. Future translation agents would involve extra features like selective usage of other MTL models as tool calls. **Depends on:** s0.1.14, s0.1.15, s0.1.16.
- ✅ (s0.1.18) Initial QA Checks (Deterministic) — Create deterministic and automated checks for formatting and completeness to enforce guardrails. **Depends on:** s0.1.01, s0.1.17.
- ✅ (s0.1.19) Initial Phase Agent: QA — Create an initial agent to act in the QA phase. Candidates include (but are not limited to): inaccurate translation detection, style-guide adherence critic, incorrect pronoun usage detection, etc. **Depends on:** s0.1.14, s0.1.18.
- ✅ (s0.1.20) Initial Phase Agent: Edit — Create our main editor agent, which will take in translated lines and apply targeted fixes based on QA findings for iterative improvements. Future editor agents would involve extra features like flagging a line for full retranslation, or using tools for more complex fixes. **Depends on:** s0.1.14, s0.1.17, s0.1.19.
- ✅ (s0.1.21) Observability Surface (CLI Status Viewer) — Display live phase status and completion summaries for trust and clarity. **Depends on:** s0.1.02, s0.1.06, s0.1.10, s0.1.11.
- ✅ (s0.1.22) Functional Onboarding — Guide users to a first successful run with defaults and validation. **Depends on:** s0.1.11, s0.1.13, s0.1.15–s0.1.20, s0.1.29, s0.1.31.
- ✅ (s0.1.23) Unit Test Coverage Gate (>80%) — Enforce unit test coverage threshold across core and CLI packages. **Depends on:** s0.1.01–s0.1.13.
- ✅ (s0.1.24) Integration Test Suite — Validate CLI workflows and runtime wiring across storage and BYOK endpoints. **Depends on:** s0.1.11, s0.1.12, s0.1.13, s0.1.23.
- ✅ (s0.1.25) Quality Test Suite — Real-LLM smoke tests for runtime and agent behaviors. **Depends on:** s0.1.14, s0.1.15–s0.1.20, s0.1.23.
- (s0.1.26) Standards Review: Declarative Agent Config — Lock in agent configuration conventions and documentation. **Depends on:** s0.1.14–s0.1.16.
- ✅ (s0.1.27) End-to-End Logging & Error Surfacing — Ensure full logging coverage and raise actionable errors instead of silent failures. **Depends on:** s0.1.06, s0.1.07, s0.1.14–s0.1.16.
- ✅ (s0.1.28) OpenRouter Full Support - Ensure that both local models and openrouter models are fully capable, using tools, and work reliantly. **Depends on:** s0.1.12, s0.1.13, s0.1.14.
- ✅ (s0.1.29) Project Bootstrap Command — Add `rentl init` to create a project from the template with sample data and config defaults. **Depends on:** s0.1.01, s0.1.03, s0.1.11.
- ✅ (s0.1.30) Onboarding Docs Pack — Quickstart, first-run tutorial, and troubleshooting checklist. **Depends on:** s0.1.22, s0.1.29.
- ✅ (s0.1.31) CLI Help/Doctor Commands — `rentl help`, `rentl doctor`, and `rentl explain <phase>` for actionable diagnostics. **Depends on:** s0.1.06, s0.1.11, s0.1.12.
- ✅ (s0.1.32) Sample Project + Golden Artifacts — Small free-to-share script with expected artifacts for smoke tests (license verified, e.g., CC BY-NC-ND). **Depends on:** s0.1.03, s0.1.04, s0.1.24, s0.1.29.
- ✅ (s0.1.33) Config Schema Versioning + Migrate — Versioned config with `rentl migrate` and a schema changelog. **Depends on:** s0.1.01.
- ✅ (s0.1.34) Log Redaction & Safety Audit — Enforce secret redaction in logs and artifacts. **Depends on:** s0.1.06, s0.1.27.
- ✅ (s0.1.35) CLI Exit Codes + Error Taxonomy — Stable exit codes for CI and scripting. **Depends on:** s0.1.06, s0.1.11.
- ❌ (s0.1.36) Deterministic Rerun Validation — Closed as impractical; LLM pipelines are chaotic systems and true determinism is outside our control. Addressed via benchmark harness and caching where it matters.
- ✅ (s0.1.37) Benchmark Harness v0.1 — Curated small evaluation set with baseline MTL comparison; runnable outside default CI. **Depends on:** s0.1.17, s0.1.19, s0.1.20.
- (s0.1.38) Benchmark Transparency Pack — Publish configs, prompts, rubric, and input/output hashes with a provenance and verification guide (no text release). **Depends on:** s0.1.37.
- ✅ (s0.1.39) Install Verification (uvx/uv tool) — Validate install + `rentl init` + full run on a clean environment. **Depends on:** s0.1.29, s0.1.24.
- ✅ (s0.1.40) Model Default Updates — Replace outdated model presets with modern open-weight defaults; require explicit model_id in config. **Depends on:** s0.1.29, s0.1.13, s0.1.14.
- ✅ (s0.1.41) Documentation Overhaul for v0.1 Release — CHANGELOG, Getting Started guide, architecture overview, data schema reference, and license/legal review. **Depends on:** s0.1.39, s0.1.30.

**Success Criteria:**
- A new user can run `rentl init` → full pipeline → export without manual edits
- No secrets appear in logs or artifacts (redaction verified)
- Small benchmark set beats baseline MTL on the rubric
- Benchmark report verifiable via published configs, rubric, and hashes
- Full-script run completes end-to-end without fatal errors (Katawa Shoujo Ren'Py script under CC BY-NC-ND or licensed equivalent)
- Onboarding docs + help/doctor resolve first-run issues in a clean environment

---

## v0.2: Quality Leap
**User Value:** "I can run an Agentic Localization pipeline and get a decent quality patch, with the same effort"

**Primary Milestone:** Translation quality jumps from "playable but rough" to "genuinely decent" through multi-agent teams per phase.

**Key Differentiator:** Each phase becomes a cohesive "team" of agents working together—smarter context analysis, more sophisticated translation, richer QA—rather than a single sample agent.

**Scope:**
- Multiple agents per phase (tuned based on v0.1 learnings)
- Multi-agent orchestration with priority ordering and agent dependencies
- Context team: scene + route summaries, character bios, glossary curation, game info research
- Pretranslation team: idiom detection, references, speaker/subject/object roles
- Translation team: direct translator, MTL-tool translator, glossary term translator
- QA team: style checker, prose consistency, character consistency
- Edit team: direct editor + scene aligner
- Agent hooks for pre/post LLM processing
- Richer deterministic QA checks + issue categorization
- Agent iteration visibility and control
- Onboarding context building (user interview, initial glossary, context docs)
- Onboarding refinements and docs expansion
- Multi-judge evaluation with variance controls
- Public, open-licensed benchmark subset for external validation
- Third-party verification runbook and reporting format

**Spec List (Expanded):**
- (s0.2.01) Multi-Agent Phase Config Schema — Extend declarative agent config to allow multiple agents per phase, ordering, and dependencies. **Depends on:** s0.1.01, s0.1.07, s0.1.26.
- (s0.2.02) Multi-Agent Orchestrator Execution — Execute agent teams with dependency gating, retries, and deterministic artifact writes. **Depends on:** s0.2.01, s0.1.07, s0.1.09.
- (s0.2.03) Agent Result Fusion Policies — Define priority, voting, and confidence merge policies with explicit schema outputs. **Depends on:** s0.2.01, s0.2.02, s0.1.01.
- (s0.2.04) Context Team Agent: Route Summarizer — Add route-level context summaries for long narratives. **Depends on:** s0.1.15, s0.2.01.
- (s0.2.05) Context Team Agent: Character Bio Curator — Maintain structured character bios and traits. **Depends on:** s0.1.15, s0.2.01.
- (s0.2.06) Context Team Agent: Glossary Curator — Extract and maintain glossary entries from context artifacts. **Depends on:** s0.1.15, s0.2.01.
- (s0.2.07) Context Team Agent: Game Info Researcher — Use web search to curate genre, synopsis, and references (HITL-ready). **Depends on:** s0.1.14, s0.1.15, s0.2.01.
- (s0.2.08) Pretranslation Team Agent: Reference Finder — Identify references, idioms, and named entities needing special handling. **Depends on:** s0.1.16, s0.2.01.
- (s0.2.09) Pretranslation Team Agent: Speaker/Subject/Object Annotator — Disambiguate roles for pronouns and POV. **Depends on:** s0.1.16, s0.2.01.
- (s0.2.10) Translation Team Agent: MTL-Tool Translator — Tool-call MTL outputs as a secondary reference. **Depends on:** s0.1.13, s0.1.17, s0.2.01.
- (s0.2.11) Translation Team Agent: Glossary Term Translator — Translate glossary terms with consistent mapping. **Depends on:** s0.2.06, s0.1.17, s0.2.01.
- (s0.2.12) QA Team Agent: Style Checker — Enforce tone, formality, and voice constraints. **Depends on:** s0.1.19, s0.2.01.
- (s0.2.13) QA Team Agent: Consistency Validator — Detect terminology and character voice drift across scenes. **Depends on:** s0.1.10, s0.1.19, s0.2.01.
- (s0.2.14) Edit Team Agent: Scene Aligner — Align edits across a scene to resolve inconsistencies. **Depends on:** s0.1.15, s0.1.20, s0.2.01.
- (s0.2.15) Agent Pre/Post Hooks — Add pre/post LLM normalization and validation hooks per agent. **Depends on:** s0.1.14, s0.2.01.
- (s0.2.16) Richer Deterministic QA Checks — Expand checks beyond length/charset (e.g., placeholders, punctuation parity, tag safety). **Depends on:** s0.1.18.
- (s0.2.17) QA Issue Taxonomy + Report Export — Categorize QA issues and export JSON/CSV reports. **Depends on:** s0.1.10, s0.1.18, s0.1.19, s0.2.16.
- (s0.2.18) Agent Iteration Visibility & Controls — Per-agent retry limits, budgets, and status telemetry. **Depends on:** s0.1.02, s0.1.06, s0.2.02.
- (s0.2.19) Prompt/Schema/Tool Overrides — Customize agents without code via config overrides and profiles. **Depends on:** s0.1.26, s0.2.01.
- (s0.2.20) Onboarding Context Building — Interview users at init to seed glossary terms and context docs. **Depends on:** s0.1.29, s0.1.11, s0.2.06.
- (s0.2.21) Multi-Judge Evaluation + Variance Analysis — Reduce scoring variance with multiple judges and rubric consolidation. **Depends on:** s0.1.37, s0.1.39.
- (s0.2.22) Public Benchmark Subset — Package an open-licensed subset with fixtures for external validation. **Depends on:** s0.1.39, s0.2.21.
- (s0.2.23) Third-Party Verification Runbook — Provide reproducibility guide and reporting template for external reruns. **Depends on:** s0.1.39, s0.2.22.
- (s0.2.24) Onboarding Refinements + Docs Expansion — Expand guides for multi-agent setup and benchmarking. **Depends on:** s0.1.30, s0.2.19, s0.2.20.
- (s0.2.25) Fusion Audit Trail — Record which agent outputs were selected, merged, or overridden with traceable rationale. **Depends on:** s0.2.02, s0.2.03, s0.1.06.
- (s0.2.26) Benchmark Verification CLI — Provide a command to validate published hashes and benchmark provenance without text release. **Depends on:** s0.1.38, s0.2.23.

**Success Criteria:**
- Benchmarks show consistent quality lift over v0.1 and baseline MTL
- Multi-agent pipelines complete reliably across all phases
- QA reports categorize issues with low variance across runs
- Documentation enables prompt/schema/tool customization without code edits
- Onboarding captures usable context/glossary before first run
- Public benchmark subset enables external reruns without licensing friction
- Third-party verification reports align with internal benchmark results

---

## v0.3: Scale & Ecosystem
**User Value:** "I can run an Agentic Localization pipeline and get multiple decent patches, and it works for my game out of the box (for popular engines)"

**Primary Milestone:** Multi-language support and game engine integration unlock localization at scale.

**Key Differentiator:** One core context setup (context and pretranslation) localizes into N languages, and your favorite game engine works out of the box—no custom schema wrangling.

**Scope:**
- Multi-language batch orchestration (run N languages in parallel / sequential with shared work)
- Language-specific profiles and settings
- Cost controls and token usage tracking across languages
- Adapter interfaces framework and SDK
- Engine-specific adapters: RPG Maker, Ren'Py, Kirikiri, SiglusEngine
- Engine-specific QA tools (known charset limitations, line lengths, word-wrapping, etc.)
- Clear contribution path for new adapters
- Batch management for large multi-language projects
- Multi-language progress tracking and reporting

**Spec List (Expanded):**
- (s0.3.01) Multi-Language Orchestrator — Run N languages sequentially or in parallel with shared upstream artifacts. **Depends on:** s0.1.07, s0.1.09, s0.2.01, s0.3.02.
- (s0.3.02) Language Profile Schema — Per-language config overrides (model, glossary, QA rules, formatting). **Depends on:** s0.1.01, s0.1.33.
- (s0.3.03) Shared Context Cache — Reuse context/pretranslation artifacts across languages with invalidation rules. **Depends on:** s0.1.05, s0.1.09, s0.3.01.
- (s0.3.04) Cost & Token Budgeting — Track and cap costs per language and per phase. **Depends on:** s0.1.06, s0.2.16, s0.3.01.
- (s0.3.05) Multi-Language Progress Viewer — Aggregate progress and errors across languages. **Depends on:** s0.1.21, s0.3.01, s0.3.02.
- (s0.3.06) Adapter SDK + Templates — Standard interface and scaffolding for engine adapters. **Depends on:** s0.1.01, s0.1.03, s0.1.04.
- (s0.3.07) Ren'Py Adapter v1 — Out-of-box import/export + QA rules for Ren'Py. **Depends on:** s0.3.06, s0.3.11, s0.2.14.
- (s0.3.08) RPG Maker Adapter v1 — Out-of-box import/export + QA rules. **Depends on:** s0.3.06, s0.3.11, s0.2.14.
- (s0.3.09) Kirikiri Adapter v1 — Out-of-box import/export + QA rules. **Depends on:** s0.3.06, s0.3.11, s0.2.14.
- (s0.3.10) SiglusEngine Adapter v1 — Out-of-box import/export + QA rules. **Depends on:** s0.3.06, s0.3.11, s0.2.14.
- (s0.3.11) Engine QA Rules Pack — Charset, line length, wrapping, and tag rules per engine. **Depends on:** s0.2.16.
- (s0.3.12) Adapter Test Harness — Fixtures + integration tests per engine adapter. **Depends on:** s0.1.24, s0.3.06, s0.3.11.
- (s0.3.13) Batch Management CLI — Run, pause, resume, and report on multi-language batches. **Depends on:** s0.1.11, s0.3.01, s0.3.02.
- (s0.3.14) Adapter Contribution Guide — Docs + examples for community adapter creation. **Depends on:** s0.3.06.

**Success Criteria:**
- A single project can localize into 3+ languages in one workflow
- Engine adapters work out of the box for the top four target engines
- Multi-language runs complete predictably with clear cost visibility

---

## v0.4: HITL Support
**User Value:** "I can run an Agentic Localization pipeline, and lend my experience to hone the results into multiple high quality patches, for my game out of the box (for popular engines)"

**Primary Milestone:** HITL support for decision making items is enabled, allowing users to be an active participant in the localization.

**Key Differentiator:** The user's own expertise and game knowledge is used to transform patches from merely decent, to high quality.

**Scope:**
- Agents can selectively escalate decision making to the user without blocking the pipeline
- HITL is configurable per agent and never prevents completion
- Feedback ingestion for human editors to add notes and trigger targeted retranslations/edits

**Spec List (Expanded):**
- (s0.4.01) HITL Message Schema — Standardize agent request, user response, and resolution payloads with IDs and phase context. **Depends on:** s0.1.01, s0.1.06.
- (s0.4.02) Non-Blocking HITL Queue — Allow agents to submit questions without halting phase execution. **Depends on:** s0.1.05, s0.1.07, s0.1.09, s0.4.01.
- (s0.4.03) HITL Response Ingestion — Accept user responses and attach them to the originating request. **Depends on:** s0.4.01, s0.4.02, s0.1.11.
- (s0.4.04) Agent Re-Run on HITL Resolution — Re-run the requesting agent with the resolved context and persist updated artifacts. **Depends on:** s0.4.02, s0.4.03, s0.1.07, s0.1.09.
- (s0.4.05) Feedback Intake Formats — Support user-submitted feedback for context, translation, QA, and edits (structured JSONL + CLI). **Depends on:** s0.1.01, s0.1.11.
- (s0.4.06) Feedback Routing Rules — Route feedback to the correct phase agents and artifacts with provenance. **Depends on:** s0.4.05, s0.1.07, s0.1.09.
- (s0.4.07) Live Patch Refresh — Apply feedback-triggered edits and regenerate export artifacts within minutes. **Depends on:** s0.4.04, s0.4.06, s0.1.04, s0.1.05.
- (s0.4.08) HITL + Feedback Status Viewer — Surface pending requests, responses, and applied changes in the CLI/TUI status viewer. **Depends on:** s0.1.21, s0.4.01, s0.4.02, s0.4.06.
- (s0.4.09) HITL Audit Trail — Record all human inputs, agent decisions, and resulting changes for traceability. **Depends on:** s0.1.05, s0.1.06, s0.4.01.
- (s0.4.10) Feedback Conflict Resolution — Define precedence rules when user edits conflict with agent outputs. **Depends on:** s0.4.06, s0.4.09.
- (s0.4.11) Optional HITL Escalation Policies — Configure which agents can ask questions and when they do so. **Depends on:** s0.2.19, s0.4.01.
- (s0.4.12) Iteration Loop Controls — Configure background improvement cycles while users playtest. **Depends on:** s0.4.06, s0.4.07.

**Success Criteria:**
- Agents can request feedback and proceed without blocking the pipeline
- Users can submit feedback tied to line IDs and receive a new patch in minutes
- HITL runs produce measurable quality improvements versus non-HITL runs
- Live feedback can be applied during active runs without corrupting artifacts

---

## v0.5: UX Polish
**User Value:** "I can run an Agentic Localization pipeline, and lend my experience to hone the results into multiple high quality patches, for my game out of the box (for popular engines), all from a convenient and nice TUI"

**Primary Milestone:** Complete TUI makes the entire workflow accessible without CLI mastery.

**Key Differentiator:** From setup to shipping, everything is doable from a polished, intuitive interface—no more terminal command memorization.

**Scope:**
- Complete TUI surface (beyond read-only status viewer)
- Interactive setup wizard (guided configuration, context input, model selection)
- Real-time progress monitoring with visual phase tracking
- QA review interface (view flagged lines, add reviewer notes inline)
- Edit workflow UI (triage issues, trigger edit cycles, preview fixes)
- HITL support for both agents requesting decisions and user-submitted feedback
- Multi-language batch management UI
- Project and configuration management screens
- Visual dashboards for QA reporting and iteration analytics
- Settings and preferences interface
- Localization-ready UI strings (catalog-driven)
- Functional onboarding refinements
- Async usage audit: Refactor CLI configuration loading to be fully async


**Spec List (Expanded):**
- (s0.5.01) TUI Architecture Plan — Define app structure, state model, navigation map, and service boundaries as a thin adapter over core. **Depends on:** s0.1.21.
- (s0.5.02) TUI App Scaffold — Textual app shell, screen registry, and routing with theme defaults. **Depends on:** s0.5.01.
- (s0.5.03) TUI State Store — Centralized state model synced from core events and run artifacts. **Depends on:** s0.5.01, s0.1.06.
- (s0.5.04) Core API Surface for TUI — Expose core domain APIs needed by TUI without duplicating logic. **Depends on:** s0.1.07, s0.1.11, s0.5.01.
- (s0.5.05) Layout System + Design Tokens — Shared components, spacing, typography, and color tokens. **Depends on:** s0.5.02.
- (s0.5.06) TUI String Catalogs — All UI text loads from locale files with fallback defaults. **Depends on:** s0.5.02.
- (s0.5.07) Project Dashboard Screen — Overview of project, run history, and quick actions. **Depends on:** s0.5.02, s0.5.03, s0.5.04, s0.5.06.
- (s0.5.08) Setup Wizard Screen — Guided project setup (config, models, sources) using core validations. **Depends on:** s0.5.04, s0.5.05, s0.5.06.
- (s0.5.09) Run Planner Screen — Phase selection, sharding, and concurrency settings. **Depends on:** s0.1.08, s0.5.04, s0.5.05, s0.5.06.
- (s0.5.10) Live Progress Screen — Phase status, per-line counts, and run events in real time. **Depends on:** s0.1.21, s0.5.03, s0.5.04, s0.5.06.
- (s0.5.11) QA Review Screen — Filter, inspect, and annotate QA issues with export hooks. **Depends on:** s0.2.17, s0.5.04, s0.5.05, s0.5.06.
- (s0.5.12) Edit Workflow Screen — Triage issues, trigger edit cycles, and preview diffs. **Depends on:** s0.1.20, s0.4.06, s0.5.04, s0.5.05, s0.5.06.
- (s0.5.13) HITL Inbox Screen — View and respond to agent questions and feedback requests. **Depends on:** s0.4.01, s0.4.03, s0.5.04, s0.5.05, s0.5.06.
- (s0.5.14) Feedback Submission Screen — Add context, translation, QA, or edit feedback during runs. **Depends on:** s0.4.05, s0.4.06, s0.5.04, s0.5.05, s0.5.06.
- (s0.5.15) Multi-Language Batch Screen — Manage multi-language runs and progress. **Depends on:** s0.3.01, s0.3.13, s0.5.04, s0.5.05, s0.5.06.
- (s0.5.16) Config & Profiles Screen — Edit configs, profiles, and agent overrides with schema validation. **Depends on:** s0.1.33, s0.2.19, s0.5.04, s0.5.05, s0.5.06.
- (s0.5.17) Reports & Analytics Screen — QA summaries, benchmark snapshots, token/cost views. **Depends on:** s0.2.17, s0.3.04, s0.5.04, s0.5.05, s0.5.06.
- (s0.5.18) Accessibility & Input Support — Keyboard navigation, focus states, and help shortcuts. **Depends on:** s0.5.02.
- (s0.5.19) TUI Extension Points — Plugin hooks for custom screens and components. **Depends on:** s0.5.01, s0.5.02.
- (s0.5.20) TUI Integration Tests — Screen flows and state updates in CI. **Depends on:** s0.1.24, s0.5.02, s0.5.04.

**Success Criteria:**
- End-to-end workflows are possible using only the TUI
- Non-technical users can run multi-language batches without CLI knowledge
- TUI feels polished and intuitive (not just functional)

---

## v1.0: Professional-Grade Tooling
**User Value:** "This is professional-grade tooling"

**Primary Milestone:** rentl reaches feature parity with enterprise CAT tools while maintaining the agility and accessibility that define it.

**Key Differentiator:** The combination of agentic automation, professional-grade reliability, rapid iteration, and delightful onboarding makes rentl a viable alternative to enterprise CAT stacks for small teams and a serious upgrade for fan translators.

**Scope:**
- CAT-grade feature parity: TM, glossary enforcement, comprehensive QA, reporting dashboards
- Rapid hotfix loop: issue triage, fix routing, patch generation in minutes
- Reliability and stability: 99%+ pipeline success rate, stable schemas/CLI, deprecation guides
- Delightful onboarding: guided setup, TUI help, project templates, shared configs
- Operational maturity: benchmarking framework, example repository, contributor docs

**Spec List (Expanded):**

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
| **v0.4** | "HITL Support" | User is part of the team of localizers |
| **v0.5** | "Great UX" | Complete TUI workflow |
| **v1.0** | "Professional-grade" | CAT parity + reliability + polish |

---

## Potential Future Directions

- Expanded adapter ecosystem (more engines, deeper integration)
- Hosted service layer with team collaboration features
- Advanced agent orchestration and auto-tuning
- Community marketplace for agent configurations and templates
- Enterprise features (SSO, audit logs, advanced permissions)
- Docker Compose support for collaborative/production deployments with hosted alternatives (PostgreSQL, hosted vector DB, etc.)
