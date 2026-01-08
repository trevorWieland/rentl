---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/analysis/brainstorming-session-2026-01-06T17:02:52Z.md
  - _bmad-output/planning-artifacts/research/technical-python-agent-workflow-frameworks-and-rag-vector-research-2026-01-07T16:50:29Z.md
date: 2026-01-07
author: rentl dev
---

# Product Brief: {{project_name}}

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

rentl is an open-source, BYOK agentic localization pipeline that makes professional-quality game localization as easy as simple MTL. It targets both fan translators and professional localization teams by combining context intelligence, phase-based agents, and strict schemas to deliver reliable, fast, and higher-quality translations. The goal is to make a "v1" translation achievable in under 24 hours, with further iterations driven by playtests and feedback-not months of manual rework.

---

## Core Vision

### Problem Statement

game localization is either slow and expensive (enterprise CAT workflows) or fast but low-quality (MTL-only fan translations). The effort barrier for professional-grade localization is so high that most fan projects default to raw LLM output, while pro pipelines take months or years.

### Problem Impact

The market is being flooded with low-effort, low-quality translations-sometimes even sold as "fan" work-eroding audience trust and killing motivation for higher-effort translations. Meanwhile, official releases remain glacial, dampening hype and leaving audiences with sub-par options.

### Why Existing Solutions Fall Short

- Enterprise CAT tools (e.g., Trados, memoQ, Crowdin) are expensive, cumbersome, and optimized for large teams-not rapid, accessible workflows.
- Fan workflows often rely on ad-hoc LLM prompting or spreadsheets, producing inconsistent quality and little accountability.
- MTL-only pipelines are fast but lack context, QA rigor, and reliable phase structure.

### Proposed Solution

rentl delivers a one-stop, agentic localization pipeline: ingest -> context -> source analysis -> translate -> QA -> edit -> export. v0.1 already improves on MTL-only flows with context-aware translation, token QA, and one agent per phase. The product aims to enable an end-to-end translation pass and playable patch within 24 hours, with later iterations focused on refinement.

### Key Differentiators

- Context intelligence + agent orchestration as the core engine, not an add-on.
- Strict schemas and observability to make outputs reliable and auditable-even for pro-grade expectations.
- Open source + BYOK: no lock-in, no cost barrier, and maximal flexibility.
- Phase-based pipeline that makes quality and progress measurable, not ad-hoc.
## Target Users

### Primary Users

**Persona 1: Alex (Fan Translator, Solo/Small Team)**
- **Context:** A passionate fan who discovers untranslated games and wants to ship a playable patch quickly. Works evenings/weekends, limited budget, light technical tooling.
- **Motivations/Goals:** Ship a v1 translation in under 24 hours; raise quality above raw MTL; keep momentum without burnout.
- **Problem Experience:** Current workflow is ad-hoc (LLM prompts + manual cleanup). High effort barrier makes pro-quality feel out of reach.
- **Success Vision:** A single run produces translated + QA'd + edited text with context applied; only iterative polish remains.

**Persona 2: Maya (Localization Lead, Pro Team)**
- **Context:** Leads a small professional localization team. Used to enterprise CAT tools, strict quality standards, and delivery timelines.
- **Motivations/Goals:** Improve quality and consistency while reducing cycle time; keep workflows auditable and repeatable.
- **Problem Experience:** CAT tools are heavy and expensive; workflow is slow, lacks agentic automation, and doesn't scale gracefully.
- **Success Vision:** Reliable, schema-driven pipeline with observability that produces high-quality outputs quickly and predictably.

### Secondary Users

- Studios/Publishers: Want faster localization turnaround without sacrificing quality or escalating costs.
- End Players/Audience: Want trustworthy translations; currently suffer from low-quality MTL releases and label confusion.
- Community Beta Testers/Reviewers: Provide feedback and refinements after v1; help validate quality and edge cases.

### User Journey

**Fan Translator Journey**
- **Discovery:** Finds rentl through community or OSS channels.
- **Onboarding:** Uses a simple setup to ingest text and configure minimal context.
- **Core Usage:** Runs the full pipeline (context -> translate -> QA -> edit) and exports a patch.
- **Success Moment:** A playable, coherent v1 translation is ready within 24 hours.
- **Long-term:** Iterates with playtest feedback, refining quality instead of rebuilding from scratch.

**Pro Team Journey**
- **Discovery:** Learns about rentl as a lighter, faster alternative to enterprise CAT stacks.
- **Onboarding:** Defines standards, schemas, and context inputs for reliable outputs.
- **Core Usage:** Uses phase-based agents with observability to track progress and quality.
- **Success Moment:** Faster release cycles without sacrificing professional-grade rigor.
- **Long-term:** Integrates rentl into a repeatable localization workflow with reliable QA signals.
## Success Metrics

**Headline Metrics (User Success)**

1) **Translation Quality Benchmark (v0.x or separate repo)**
- **Method:** LLM-judge using a high-reasoning model (e.g., GPT-5.2).
- **Rubric:**
  - Translation accuracy
  - Tone/prose style fidelity
  - Cross-line consistency
- **Comparison Baselines:** simple MTL pass, professional translation, rentl pipeline.
- **Status:** Benchmark framework planned; initial results reported without hard targets.

2) **Time to First Playable Patch (v1 translation)**
- **Definition:** End-to-end pipeline completion time from ingest to export.
- **Target Range:** Hours (not days).
- **Measurement:**
  - Wall-clock time
  - Human effort hours
  - LLM token usage

**User Value Signal**
- **Aha Moment:** "Already?" reaction when a playable patch is ready after context -> pretranslation -> translation -> QA -> edit.

### Business Objectives (OSS Health Signals)

- **Projects Completed:** Count of end-to-end localization runs that finish successfully.
- **Community Adoption:** GitHub stars, forks, contributors, and downstream usage signals (tracked if feasible).
- **Note:** OSS health is directional, not a hard business KPI.
## MVP Scope

### Core Features (v0.1)

- **End-to-end pipeline, minimal but complete:** Init -> Ingest -> Context -> Source Analysis -> Translate -> Target QA -> Edit -> Export
- **Baseline improvement over simple MTL:** MTL pass plus minimal context building, pretranslation, QA, and edit looping
- **Minimal agent set (one per phase):**
  - Context: Scene summarizer
  - Source analysis: Idiom/reference detector
  - Translate: Context-aware line translator
  - Target QA: Style checker (standards file required)
  - Edit: Retranslator (source + prior translation + QA notes)
- **CLI-first workflow:** Hybrid interactive setup -> config -> batch run
- **Minimal data formats:** CSV + JSONL + TXT
- **OpenAI-compatible endpoints:** BYOK model support
- **Strict schemas + observability:** Deterministic completion, clear status visibility, error transparency

### Out of Scope for MVP (v0.1)

- GUI/TUI completeness
- Large agent catalogs or multi-agent per phase
- Benchmarks and formal quality scoring (planned for v0.x or later)
- Advanced adapters or engine-specific integrations
- Hosted service layer, pricing, or closed-source features
- OCR, piracy tooling, or non-game translation scope

### MVP Success Criteria

- Produces higher-quality output than simple MTL in real usage
- Delivers a first playable patch in hours, not days
- End-to-end pipeline runs deterministically and is repeatable
- Users can complete a full project without expert intervention

### Future Vision (v1.0)

- **Full agentic localization pipeline:** Multiple agents per phase with richer context and QA depth
- **Quality benchmarks:** LLM-judge framework with rubric (accuracy, style, consistency)
- **TUI/GUI completeness:** User-friendly interface and onboarding wizards
- **Guides and onboarding:** How-to documentation, quickstart flows, and best-practice guidance
- **Expanded observability:** Phase dashboards, history, and structured QA reports