# Product Mission

## Pitch

rentl is an open-source, BYOK agentic localization pipeline that makes professional-grade game translation feel as easy and fast as simple MTL. It delivers a coherent, playable v1 translation in hours through a phase-based workflow (ingest → context → source analysis → translate → QA → edit → export), targeting both fan translators seeking accessibility and professional localization teams demanding reliability and quality.

## Users

### Primary Customers

- **Fan translators (solo/small teams):** Passionate individuals working nights and weekends who need a structured way to ship playable patches quickly without burnout. They want professional-quality output without enterprise overhead or complex tooling.

- **Professional localization teams:** Small to medium teams seeking faster release cycles without sacrificing quality and consistency. They need reliable, auditable outputs and observability without the heavy cost and complexity of enterprise CAT tools.

### User Personas

**Alex Rivera (Fan Translator)**
- **Role:** Solo fan translator working evenings/weekends
- **Context:** Discovers untranslated games and wants to share them with communities. Limited budget, lightly technical, driven by passion for games and language.
- **Pain Points:** Ad-hoc LLM prompts and manual cleanup produce inconsistent quality; high effort barrier makes professional-grade translation feel out of reach; constant friction kills momentum.
- **Goals:** Ship a playable v1 translation in under 24 hours; raise quality above raw MTL; maintain sustainable workflow without burnout.

**Maya Chen (Localization Lead)**
- **Role:** Localization lead at a small professional team
- **Context:** Manages a team delivering localizations for commercial releases. Used to enterprise CAT tools with strict quality standards and delivery timelines.
- **Pain Points:** Enterprise CAT tools are expensive and cumbersome; workflow is slow and lacks agentic automation; difficult to scale across multiple projects or partner studios.
- **Goals:** Improve quality and consistency while reducing cycle time; maintain auditable, repeatable workflows; deliver professional-grade results faster.

**Quinn Alvarez (QA Editor)**
- **Role:** QA editor and patch triage specialist
- **Context:** Spends days reconciling scattered feedback, hunting for similar issues, and ensuring edits don't break formatting or context across thousands of lines.
- **Pain Points:** Manual triage is slow and error-prone; fixes can ripple unexpectedly across scripts; hard to maintain consistency when patching based on reviewer feedback.
- **Goals:** Apply fixes consistently across similar lines; reduce time between feedback review and patch release; maintain tone and style integrity during edits.

## The Problem

### Game Localization is Broken at Both Ends

Game localization sits in a painful middle ground. Enterprise CAT tools (Trados, memoQ, Crowdin) are expensive, cumbersome, and optimized for large teams rather than rapid, accessible workflows. They introduce months of setup, complex licensing, and steep learning curves that make them impractical for fan projects and small studios.

Meanwhile, fan translators default to raw MTL or ad-hoc LLM prompting—fast but producing inconsistent, low-quality translations that damage audience trust. The effort barrier to professional-grade localization is so high that most fan projects never achieve it, while official releases remain glacially slow, leaving audiences with sub-par options.

The result is a flooded market of low-effort translations and frustrated players, while passionate translators burn out trying to bridge the quality gap with primitive tools.

**Our Solution:** rentl provides a structured, phase-based agentic pipeline that makes professional-quality localization accessible. By combining context intelligence, multi-agent orchestration, and strict schemas, rentl delivers a coherent, playable v1 translation in hours—then supports rapid iteration through automated QA, edit cycles, and observability.

## Differentiators

### BYOK Model Flexibility

Unlike locked-in translation platforms that force you into their proprietary models or pricing, rentl lets you bring any OpenAI-compatible endpoint. Use OpenAI, OpenRouter, local models via Ollama, or LM Studio—switch models anytime without changing your workflow. This results in complete control over cost, quality, and data privacy.

### Process Over Model

Unlike tools that treat LLM translation as a magic black box, rentl recognizes that the real gap in game localization is process, structure, and iteration—not model capability. Our phase-based pipeline (context → analysis → translate → QA → edit) provides the systematic rigor that elevates LLM output from raw MTL to professional quality. This results in consistent, auditable translations with clear improvement paths.

### Democratized CAT Workflows

Unlike enterprise CAT tools that hide glossaries, translation memory, QA checks, and style enforcement behind expensive licenses, rentl brings these professional-grade features to everyone through agentic automation. Fan projects now have access to the same quality scaffolding as major studios, without the enterprise overhead. This results in a massive leap in translation quality for the broader community.

### Iterative Localization as First-Class Workflow

Unlike one-and-done translation tools that assume a single pass is sufficient, rentl is built around rapid iteration. Playtest feedback triggers quick edit cycles; reviewer notes route to an editor agent that applies fixes consistently across similar lines; each iteration tightens quality without rebuilding from scratch. This results in a sustainable workflow where quality improves continuously rather than requiring complete rework.

## Key Features

### Core Features

- **Phase-based pipeline orchestration:** Run a complete localization pipeline (ingest → context → source analysis → translate → QA → edit → export) with deterministic completion and clear phase boundaries, enabling reliable, reproducible translation workflows.

- **BYOK model integration:** Configure any OpenAI-compatible endpoint (custom URL + API key) and switch models per phase or per run, giving users complete control over quality, cost, and model choice without tool reconfiguration.

- **Context-aware translation:** Automatically associate scene, route, and line context with source text, then apply that context during translation to maintain coherence across the entire script.

- **Multi-format support:** Ingest source text from CSV, JSONL, or TXT formats and export localized outputs suitable for patching, with clear schema validation throughout the pipeline.

### Collaboration Features

- **Structured review workflow:** Reviewers can submit issue reports tied to specific line IDs or scenes, which editors can triage and use to trigger targeted edit cycles that apply fixes consistently.

- **QA reporting and iteration tracking:** View per-line or per-scene QA pass/fail breakdowns, track iteration counts, and review what changed between pipeline runs or patch versions.

- **Glossary and style management:** Define and maintain glossaries and style guidance that are enforced across translation runs, ensuring terminology and tone consistency throughout the project.

### Advanced Features

- **Observability and progress tracking:** Monitor pipeline progress by phase and overall status with detailed telemetry, including agent iteration counts, token usage, and completion timestamps—all accessible via CLI and optional TUI.

- **Benchmarking and quality evaluation:** Compare translation outputs against baseline MTL translations and official translations using LLM-judge rubrics (accuracy, style fidelity, consistency) to measure quality improvements.

- **Rapid hotfix loop:** When a reported issue is identified, the edit agent can triage the problem, fix similar instances across the script, and ship a new patch within minutes—making quality iteration immediate and actionable.

- **Multi-language batch orchestration:** Run translation workflows across multiple languages in parallel with language-specific profiles, cost controls, and batch management for large-scale localization projects.
