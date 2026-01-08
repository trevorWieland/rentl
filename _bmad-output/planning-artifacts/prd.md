---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-rentl-2026-01-07.md
  - _bmad-output/planning-artifacts/research/technical-python-agent-workflow-frameworks-and-rag-vector-research-2026-01-07T16:50:29Z.md
  - _bmad-output/analysis/brainstorming-session-2026-01-06T17:02:52Z.md
workflowType: 'prd'
lastStep: 11
documentCounts:
  briefs: 1
  research: 1
  brainstorming: 1
  projectDocs: 0
---

# Product Requirements Document - rentl

**Author:** rentl dev
**Date:** 2026-01-07T16:05:42-06:00

## Executive Summary

rentl is an open-source, BYOK agentic localization pipeline for games that makes professional-grade translation feel as easy as MTL. v0.1 is CLI-first with a hybrid setup -> config -> batch flow, while v1.0 targets a full GUI (web or desktop, TBD). The system runs a phase-based pipeline - ingest -> context -> source analysis -> translate -> QA -> edit -> export - so a single invocation can produce a playable v1 translation in hours, not days, with human review focused on polish rather than rework. It serves both fan translators (speed + accessibility) and professional localization leads (quality + consistency) by prioritizing reliability, schema-driven outputs, and clear progress visibility.

### What Makes This Special

rentl's differentiator is its BYOK model strategy and CAT-grade pipeline ambition. BYOK means users bring any OpenAI-compatible endpoint (custom URL + key), enabling OpenAI, OpenRouter, or local models via tools like Ollama and LM Studio. The agentic pipeline is designed to punch above its weight against CAT tools: glossaries, translation memory, QA checks, term/style enforcement, and reporting/observability are treated as v1.0 must-haves. The "moment of truth" is a first-pass agentic localization run that feels like a generational leap beyond single-pass MTL - producing a v1 that is ready for human feedback immediately.

## Project Classification

**Technical Type:** developer_tool  
**Domain:** general  
**Complexity:** low  
**Project Context:** Greenfield - new project

rentl is best classified as a developer tool: an extensible, open-source pipeline and agent framework with a CLI surface now and a GUI surface later. The domain is general software tooling (not a game itself), and there are no regulatory burdens driving domain complexity, even though the product aims for enterprise-grade feature parity over time.

## Success Criteria

### User Success

- A single pipeline invocation yields a playable v1 translation that feels like a generational leap over single-pass MTL, ready for human feedback immediately.
- Users can complete a full human review pass in the time it takes to play the game normally, with one-off notes routed to an editor agent for rapid v1.1 patching.
- Time to first playable patch targets: ~2 hours of bootstrap/setup + ~6 hours runtime (variation expected by game scale, model choice, and parallelization).

### Business Success

- Primary success is personal utility and ongoing use (OSS-first: "If it suits me, it is a success").
- Optional community signal: 100 GitHub stars within 12 months of v1.0 release (directional, not a hard KPI).

### Technical Success

- 99% full pipeline run success rate (failures treated as bugs, not expected variance).
- Track iteration quality metrics: percent of lines passing quality checks after 1, 2, and 3 iterations; use these to guide prompt/agent improvements (targets set per game/model).
- Reliability and observability reports are first-class: progress rollups, agent iteration counts, and quality pass/fail breakdowns to enable debugging and improvement.

### Measurable Outcomes

- Time to first playable patch: ~2 hours setup + ~6 hours runtime.
- Pipeline reliability: >=99% successful end-to-end runs.
- Quality benchmarking: LLM-judge with a 3-prong rubric (accuracy, style fidelity, consistency) comparing rentl vs MTL and vs official translations on real games with released translations.
- Iteration efficiency: percent of lines passing quality checks after N iterations (N and thresholds set per project/model).
- Optional OSS signal: 100 stars within 12 months of v1.0 (directional).

## Product Scope

### MVP - Minimum Viable Product

- Bare-minimum MTL pass plus 1 agent per phase (context, source analysis, translation, QA, edit).
- End-to-end pipeline that is already a better experience and result than simple MTL.
- CLI-first, hybrid setup -> config -> batch run.

### Growth Features (Post-MVP)

- Each 0.x.0 release adds: more agents, more automated quality checks, UX polish, and delivery surface improvements (GUI/TUI/web app).

### Vision (Future)

- v1.0 success = weekend v2 translation workflow: bootstrap Friday night, run/iterate overnight, playthrough Saturday with agentic edits, and release by Sunday night.
- Dream hotfix loop: a reported issue triggers an editor agent to triage, fix similar instances, and ship a new patch within ~5 minutes.

## User Journeys

**Journey 1: Alex Rivera - Shipping a Playable Patch in a Weekend**  
Alex is a fan translator working nights and weekends on a game they love. Their workflow is ad-hoc: raw LLM prompts, manual cleanup, and lots of context hunting. The friction is constant and the quality is inconsistent, which kills momentum. While browsing OSS localization channels, Alex finds rentl and sees a pipeline that promises structure without enterprise overhead.

Alex starts with a simple setup: ingest the script, add minimal context, and kick off the pipeline. As the system moves through context, source analysis, translation, QA, and edit, Alex can see progress by line and scene. The breakthrough comes when the pipeline finishes and a playable v1 patch is ready in under 24 hours. It is coherent, consistent, and already better than raw MTL.

After that, Alex plays the game, leaving one-off notes and kicking off quick edit cycles. Instead of rebuilding, each iteration tightens quality. The new reality is that translation work feels sustainable: Alex can ship a v1 quickly and refine based on playtest feedback without burning out.

**Journey 2: Maya Chen - Delivering Pro-Grade Quality Faster**  
Maya leads a small localization team and is used to enterprise CAT tools, rigid QA gates, and slow cycles. Quality and consistency are non-negotiable, but the current stack is heavy, expensive, and too slow for the release cadence the team wants. Maya discovers rentl as a lighter, open-source alternative that still respects professional standards.

She onboards by defining standards, schemas, and context inputs. The team runs the phase-based pipeline with observability, seeing where QA flags appear and how edits resolve them. The critical moment is when a full run produces a reliable, auditable output that is faster than the legacy workflow without sacrificing quality or consistency.

Over time, rentl becomes a repeatable, trusted workflow in Maya's team. QA signals are clearer, turnaround is faster, and the team can maintain professional-grade rigor without the overhead and lock-in of traditional CAT tooling.

**Journey 3: Jordan Park - Community Reviewer and Beta Tester**  
Jordan is an active community reviewer who loves testing fan patches and reporting issues. They care about clarity and tone, but they do not want to learn complex tooling just to file a bug report. When a rentl-based patch drops, Jordan wants a simple way to log issues that actually get fixed.

Jordan plays the game and flags a few lines that feel off. Instead of posting vague notes in a chat server, they submit a structured report tied to line IDs and scenes. The breakthrough comes when a follow-up patch lands quickly, and the fixes are consistent across similar lines, not just the ones Jordan flagged.

The new reality is that Jordan's feedback is actionable and respected. They feel like part of a real QA loop, and patches improve quickly without the project stalling.

**Journey 4: Quinn Alvarez - QA Editor and Patch Triage**  
Quinn is a QA/editor who cares about consistency, terminology, and tone. Their day is spent reconciling scattered feedback, hunting for similar issues, and making edits that do not break formatting or context. The work is slow because each fix can ripple across the script.

With rentl, Quinn loads reviewer notes and runs an edit cycle that targets known issues. The critical moment is when the edit agent not only fixes the reported lines, but applies the same correction pattern across the script while preserving style constraints. The QA report shows what changed and why.

The new reality is faster, safer patching. Quinn can triage, edit, and export with confidence, and the team can ship v1.1, v1.2, and beyond without manual rework.

**Journey 5: Lena Sato - Language Learner and Translation Deep Dive**  
Lena is learning Japanese and wants to go beyond textbook drills. She chooses a game she loves and wants to understand how nuance, idioms, and tone shift across translations. She needs context and explanation, not just a raw translated line.

Lena runs rentl with rich context enabled and uses the outputs to compare source text, translation, QA notes, and edits. The breakthrough comes when she can see why a line was translated a certain way and how alternate phrasing changes the meaning.

The new reality is a guided translation deep dive. Rentl becomes a learning tool that makes real-world language study more immersive and precise than passive reading.

**Journey 6: Sam Patel - Indie Developer Shipping Multi-Language Releases**  
Sam is a solo indie developer with a small budget and big international ambitions. They want to release in multiple languages but cannot afford professional localization and do not want to ship low-quality AI translations that damage the game's reputation.

Sam uses rentl to bootstrap a multi-language pipeline with BYOK model control. They run translations in batches, review QA reports, and iterate on style/glossary settings for each language. The breakthrough comes when Sam ships a multi-language release that reads coherently and avoids the "raw MTL" feel.

The new reality is that localization becomes feasible for small teams. Sam can reach new markets without a large budget, and quality improves over time with each iteration.

**Journey 7: Priya Desai - Publisher Localization Program Manager**  
Priya runs localization support across multiple partner studios. Her problem is scale: every studio has different workflows, and localization quality varies wildly. She wants a standard, repeatable process that studios can adopt without a heavy enterprise contract.

Priya introduces rentl as a shared localization pipeline with standard configs, glossaries, and QA reporting. The critical moment is when a new partner studio onboards quickly, runs a full localization pass, and produces auditable outputs that meet publisher standards.

The new reality is localization as a consistent service. Priya can offer localization support as a partner feature, track quality across studios, and reduce time-to-market for localized releases.

### Journey Requirements Summary

These journeys reveal requirements for:

- Guided onboarding and CLI-first setup with clear config generation
- Script ingest, context layering, and phase-based orchestration
- Progress visibility by line/scene and clear run status
- QA reporting with pass/fail breakdowns and iteration counts
- Reviewer-friendly issue capture tied to line IDs and scenes
- Edit cycles that apply fixes consistently across similar lines
- Patch export/versioning to support rapid v1.1+ updates
- Standards, glossary, and style enforcement for consistent tone
- Explainability/traceability of translation decisions (especially for learners)
- Multi-language batch runs with cost controls and language-specific profiles
- Shared configs/templates for partner studios and portfolio-wide reporting

## Innovation & Novel Patterns

### Detected Innovation Areas

- Process over model: challenges the assumption that LLMs are not good enough for game localization; the real gap is process, structure, and iteration.
- Iterative localization as the norm: shifts fan translation from one-and-done to multiple guided edit cycles, making quality improvement practical and sustainable.
- Democratized CAT: brings CAT-grade workflows (glossaries, QA, term/style enforcement, reporting) to the general public via agentic automation.

### Market Context & Competitive Landscape

- Existing CAT tools emphasize enterprise workflows and cost barriers, while MTL tools emphasize speed with limited quality controls. rentl sits between these: fast enough for fan projects, structured enough for professional expectations.

### Validation Approach

- Benchmark against MTL and official translations using LLM-judge rubrics (accuracy, style fidelity, consistency).
- Measure iteration efficiency (how many cycles to reach target quality thresholds).
- Track time-to-v1 and user-reported quality leap perceptions after a single full run.

### Risk Mitigation

- If the innovation thesis does not validate, v0.1 still delivers a better alternative to contextless MTL through structured phases, minimal agents, and observability.
- Maintain BYOK flexibility so users can swap models and optimize quality/cost without reworking the pipeline.

## Developer Tool Specific Requirements

### Project-Type Overview

rentl is a Python-first developer tool with a CLI surface in v0.1 and a GUI surface by v1.0 (web or desktop, TBD). It is BYOK-first: users choose any OpenAI-compatible endpoint and set source/target languages with no hardcoded restrictions. The product remains open-source and template-driven for repo setup.

### Technical Architecture Considerations

- Python 3.14 baseline, managed via uv.
- Code quality and maintenance: ruff (lint/format), pytest (tests), ty (type checking).
- CLI-first runtime with config-driven pipeline execution.
- BYOK model compatibility via user-provided base URL + API key.

### Language Matrix

- Localization language selection is user-configurable from day one (no product-imposed language restrictions).
- Benchmarking focus for the author: JPN -> ENG, but not a product constraint.

### Installation Methods

- Supported installs: uv tool, uvx package, and standard PyPI distribution.
- Primary onboarding path: clone a repo generated via copier template for consistent structure and organization.

### API Surface

- Public surface includes CLI commands, config schemas, and primary agent/pipeline interfaces.
- No stability guarantees until v1.0; at v1.0, core schemas, CLI commands, and primary interfaces are frozen with a "no breaking changes" posture.

### Code Examples

- Significant examples and benchmarks live in a separate repo derived from the template (not shipped in the main repo).
- Benchmarking uses real games with official translations, compared against baseline MTL and rentl outputs.

### Migration Guide

- Semantic versioning governs releases; schema versioning is tied to semver.
- Deprecations are announced in 1.x (e.g., deprecated in 1.3.0 for removal in 2.0), with no fixed window requirement.

### Implementation Considerations

- Focus on tooling reliability and reproducibility for CLI-first workflows.
- Template-based repo setup is the default for consistent structure across projects.
- IDE integration is out of scope beyond basics until later versions.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Experience MVP  
**Resource Requirements:** Small OSS team (Python + CLI tooling + LLM integration) with contributions from the community.

**Forward-Looking Posture:**  
Design early versions so v1.0+ features do not require avoidable refactors. That means modular phase boundaries, versioned schemas, and clear CLI/config interfaces from day one, even if some capabilities are stubbed or manual.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Fan translators shipping a playable v1 quickly
- Pro leads validating structured, auditable outputs
- QA/editor iteration loops with measurable progress

**Must-Have Capabilities:**
- CLI-first setup (interactive config -> batch run)
- Ingest for CSV/JSONL/TXT
- One agent per phase (context, source analysis, translation, QA, edit)
- BYOK OpenAI-compatible endpoint config (URL + key)
- Basic QA checks + schema validation
- Progress/observability by phase/line/scene
- Export patch output

### Post-MVP Features

**Phase 2 (Post-MVP):**
- Additional agents per phase + richer QA checks
- Translation memory + glossary/term locking
- Multi-language batch orchestration + cost controls
- GUI/TUI/web app surface
- Adapter interfaces + engine-specific import/export
- Reporting dashboards + iteration analytics
- Example/benchmark repo(s)

**Phase 3 (Expansion):**
- CAT-grade feature parity (TM, glossaries, QA suites, reporting)
- Rapid hotfix loop (issue -> triage -> fix -> patch)
- Partner-studio templates and shared configs
- Strong stability guarantees for schemas/CLI with deprecation paths

### Risk Mitigation Strategy

**Technical Risks:** Model variability, convergence of iteration loops, maintaining 99% run success.  
**Mitigation:** Schema-first outputs, deterministic phase boundaries, iteration metrics, and BYOK flexibility for model swapping.

**Market Risks:** "AI translation is bad" stigma; OSS adoption friction.  
**Mitigation:** Transparent benchmarks against MTL + official translations, and a v1-ready "moment of truth" demo.

**Resource Risks:** Solo bandwidth across pipeline + UX + benchmarks.  
**Mitigation:** CLI-first focus, strict phase scope, and community-ready templates to offload setup costs.

## Functional Requirements

### Pipeline Orchestration & Configuration

- FR1: Users can create a project configuration that defines pipeline phases and settings.
- FR2: Users can run the full localization pipeline end-to-end using a saved configuration.
- FR3: Users can run individual pipeline phases independently.
- FR4: Users can re-run phases with updated inputs without re-ingesting the full project.
- FR5: Users can version and reuse project configurations across runs.

### Data Ingest & Export

- FR6: Users can ingest source text in supported file formats (CSV, JSONL, TXT).
- FR7: The system can validate ingested data against required schemas.
- FR8: Users can export localized outputs in supported formats suitable for patching.
- FR9: Users can generate updated patch outputs after edits or QA fixes.

### Context & Analysis

- FR10: Users can provide structured context inputs (e.g., scene, route, line context).
- FR11: The system can associate context with source lines for downstream phases.
- FR12: The system can surface context summaries used during translation and QA.

### Translation, QA, and Editing

- FR13: The system can perform an initial translation pass using user-provided model endpoints.
- FR14: The system can apply QA checks to translated output and flag issues.
- FR15: The system can perform edit cycles that incorporate QA findings and user notes.
- FR16: Users can submit one-off feedback notes tied to specific lines or scenes.
- FR17: The system can apply consistent fixes across similar lines when editing.

### Observability & Reporting

- FR18: Users can view pipeline progress by phase and overall status.
- FR19: Users can view per-line or per-scene status and change history.
- FR20: The system can report QA pass/fail counts and iteration counts.
- FR21: Users can review what changed between pipeline runs or patch versions.

### BYOK Model Integration

- FR22: Users can configure a custom OpenAI-compatible base URL and API key.
- FR23: Users can select models per phase or per run.
- FR24: The system can switch models without requiring project re-setup.

### Collaboration & Review

- FR25: Reviewers can submit structured issue reports tied to line IDs or scenes.
- FR26: Editors can triage review issues and trigger targeted edit cycles.
- FR27: Users can manage glossary and style guidance used across runs.
- FR28: Users can track term/style compliance status in QA results.

### Benchmarking & Evaluation

- FR29: Users can run quality evaluations comparing outputs to a baseline MTL translation.
- FR30: Users can evaluate translation quality against a defined rubric (accuracy, style, consistency).
- FR31: Users can record benchmark outcomes for comparison across runs or models.

### Extensibility & Templates

- FR32: Users can bootstrap new projects using a standard template structure.
- FR33: Users can add or modify agent configurations without changing core workflow logic.
- FR34: Users can extend supported formats via adapter interfaces.

## Non-Functional Requirements

### Performance

- The project must publish model-specific performance targets prior to v1.0 (e.g., expected runtime ranges by model and dataset scale).
- Performance regressions must be detectable by comparing runs against the published targets.
- Runtime expectations must be documented per phase and per model before v1.0 release.

### Reliability

- The pipeline must target 99% end-to-end run success on supported configurations; failures are treated as bugs.
- Reliability targets must be specified per recommended model before v1.0 (e.g., 99% with GPT-5.2).
- Given the same inputs and configuration, repeated runs must be reproducible within documented tolerances.

### Security & Privacy

- API keys must be stored locally and never logged or exposed in outputs.
- User-provided source/target content must not be transmitted anywhere except the configured model endpoint.
- Logs and reports must redact sensitive data by default.

### Scalability

- The system must support large scripts and multi-language batch workflows without requiring architectural changes.
- Batch and concurrency options must be available to manage scale and cost as datasets grow.

### Integration & Compatibility

- Model integration must adhere to OpenAI-compatible API conventions with configurable base URL and model name.
- Config schemas must be versioned and forward-compatible; breaking changes require explicit deprecations.
- Input and output formats must remain stable across minor releases.

### Maintainability & Extensibility

- Core phase boundaries must remain modular to avoid refactors when adding new agents or phases.
- The project must maintain a documented deprecation policy for schema and CLI changes post-v1.0.
