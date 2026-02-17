# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - Unreleased

**Playable Patch** — End-to-end agentic localization pipeline that produces a playable v1 translation in hours.

### Added

#### Pipeline & Orchestration
- 7-phase pipeline orchestrator with dependency gating, deterministic merges, and staleness tracking (s0.1.07)
- Per-phase execution strategies (full/scene/route) and concurrency controls (s0.1.08)
- Phase history and staleness rules — downstream outputs invalidate when upstream changes (s0.1.09)
- Phase result summaries and metrics — glossary counts, QA totals, annotation coverage (s0.1.10)
- Run persistence and artifact store protocols for durable runs and audits (s0.1.05)

#### Schemas & Validation
- Strict Pydantic schemas for configs, inputs, outputs, and artifacts (s0.1.01)
- Progress semantics and tracking with trustworthy status and completion reporting (s0.1.02)
- Config schema versioning with `rentl migrate` command and schema changelog (s0.1.33)

#### BYOK Model Integration
- BYOK config and endpoint validation for OpenAI-compatible providers (s0.1.12)
- BYOK runtime integration with pydantic-ai, retries, and backoff (s0.1.13)
- Full OpenRouter support — both local models and OpenRouter work reliably with tools (s0.1.28)
- Model default updates — modern open-weight defaults, explicit model_id required in config (s0.1.40)

#### Agents
- Agent runtime scaffold with pydantic-ai harness, TOML profiles, and 3-layer prompts (s0.1.14)
- Context agent — scene summarizer with strict validation, validated with real game data (s0.1.15)
- Pretranslation agent — idiom labeler for idiomatic expressions, puns, wordplay, and cultural phrases (s0.1.16)
- Translation agent — direct translator using context and pretranslation data (s0.1.17)
- QA agent — style-guide adherence critic for automated quality assessment (s0.1.19)
- Edit agent — targeted fixes based on QA findings for iterative improvement (s0.1.20)

#### CLI
- CLI workflow with full plan and single phase execution, clear status output (s0.1.11)
- Project bootstrap via `rentl init` with interactive setup, sample data, and config defaults (s0.1.29)
- Help, doctor, and explain commands for actionable diagnostics (s0.1.31)
- Stable CLI exit codes and error taxonomy for CI and scripting (s0.1.35)

#### I/O Adapters
- Import adapter for CSV, JSONL, and TXT with schema validation (s0.1.03)
- Export adapter for CSV, JSONL, and TXT with audit hooks and schema validation (s0.1.04)

#### Observability
- Log/event taxonomy and sink protocols for standardized observability (s0.1.06)
- CLI status viewer — live phase status and completion summaries (s0.1.21)
- End-to-end logging and error surfacing — actionable errors instead of silent failures (s0.1.27)

#### QA & Testing
- Deterministic QA checks for formatting and completeness guardrails (s0.1.18)
- Unit test coverage gate (>80%) across core and CLI packages (s0.1.23)
- Integration test suite for CLI workflows and runtime wiring (s0.1.24)
- Quality test suite — real-LLM smoke tests for runtime and agent behaviors (s0.1.25)

#### Security & Compliance
- Log redaction and safety audit — secret redaction enforced in logs and artifacts (s0.1.34)

#### Benchmark
- Benchmark harness with curated evaluation set and baseline MTL comparison (s0.1.37)

#### Samples & Onboarding
- Sample project with golden artifacts for smoke tests (CC BY-NC-ND licensed) (s0.1.32)
- Functional onboarding — guided first run with defaults and validation (s0.1.22)
- Onboarding docs pack — quickstart, first-run tutorial, and troubleshooting checklist (s0.1.30)
- Install verification via uvx/uv tool — validated on clean environment (s0.1.39)

### Not Included

- **Deterministic rerun validation** (s0.1.36) — Closed as impractical; LLM pipelines are chaotic systems and true determinism is outside our control. Addressed via benchmark harness and caching where it matters.
- **Standards review: declarative agent config** (s0.1.26) — Deferred to v0.2.
- **Benchmark transparency pack** (s0.1.38) — Deferred to v0.2.

### Known Limitations

- Single agent per phase — multi-agent teams are planned for v0.2
- No HITL (human-in-the-loop) support — planned for v0.4
- CLI-only interface — TUI planned for v0.5
- Single target language per run — multi-language support planned for v0.3
- Benchmark text (Katawa Shoujo) is CC BY-NC-ND and must be downloaded at runtime; it is not bundled in the package
