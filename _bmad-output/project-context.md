---
project_name: 'rentl'
user_name: 'rentl dev'
date: '2026-01-08T12:16:26-06:00'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'anti_patterns']
status: 'complete'
rule_count: 39
optimized_for_llm: true
existing_patterns_found: 13
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- Python 3.14 baseline.
- Pin "latest stable" versions at template generation time; refresh pins when the template is updated.
- OpenAI Python SDK: latest stable (Context7 lists v2.11.0).
- PydanticAI: latest stable (Context7 lists v1.0.5).
- FastAPI: latest stable (Context7 lists 0.128.0).
- Textual: latest stable (Context7 lists v6.6.0).
- uv: latest stable (Context7 changelog references 0.8.0).
- Typer: latest stable at template generation time.
- Chroma: latest stable at template generation time.
- ruff, ty, Copier: latest stable at template generation time.

## Critical Implementation Rules

### Language-Specific Rules (Python)

- Strict typing only: no `Any` or `object` anywhere. Use full, explicit types for all schemas, agents, tools, and APIs.
- Pydantic only (no dataclasses). Every field must use `Field(..., description="...")`.
- Async-first everywhere; design APIs and IO around `async`/`await` and modern structured concurrency.
- Use modern Python 3.14 features and patterns; avoid legacy constructs.
- Deprecation warnings must be addressed immediately (no deferral).
- Prefer frequent dependency updates to stay on latest stable features/perf.

### Framework-Specific Rules

- Typer CLI: commands are thin adapters over `rentl-core` APIs; no business logic in CLI commands.
- Textual TUI: v0.1 is read-only status/progress; design now to evolve into a full interactive surface by v1.0.
- FastAPI (future): routes are thin adapters over core service layer; no direct storage access.
- PydanticAI/OpenAI SDK: use OpenAI-compatible REST; do not bypass model adapter interfaces.
- Vector store: access only via `rentl_core.adapters.vector` protocol; default Chroma implementation behind interface.

### Testing Rules

- Tests live under `tests/unit`, `tests/integration`, `tests/quality` only.
- Use pytest markers (e.g., `unit`, `integration`, `quality`) and/or paths to select tiers; do not skip tests within a tier.
- Unit tests: fast (<250ms), mocks allowed, no external services; run the full unit tier with zero skips.
- Integration tests: BDD-style, minimal mocks, real services, no LLMs; few but high-signal; run the full integration tier with zero skips.
- Quality tests: real LLMs, no mocks; run the full quality tier with zero skips.
- Coverage is mandatory for features: tests must directly exercise intended behavior.

### Code Quality & Style Rules

- Code must pass all quality checks with zero errors, failures, or warnings.
- Ruff is the formatter; enforce 120-character line length.
- Google-style docstrings required; docstring linters must enforce both existence and formatting compliance.
- Inline/per-file ignores are suspicious and must be deeply audited; attempt removal and re-run lint/typecheck to improve code.
- Follow `snake_case` for modules/files/functions/variables and `PascalCase` for classes/types.

### Development Workflow Rules

- Address deprecation notices immediately; do not postpone to future work.
- Prefer frequent dependency updates to stay current on features/performance.
- CI/local checks must be clean: zero errors, failures, or warnings before merging.

### Critical Don't-Miss Rules

- Never use `Any` or `object` in types; always model explicit schema types.
- Never bypass adapter interfaces (model/vector/storage); go through `rentl-core` protocols.
- Never place core logic in CLI/TUI/API layers; they are thin adapters only.
- Never use inline/per-file ignores without a documented, audited justification; attempt removal first.
- Never skip tests within a tier; tests either run and pass or run and fail.

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code.
- Follow all rules exactly as documented.
- When in doubt, prefer the more restrictive option.
- Update this file if new patterns emerge.

**For Humans:**
- Keep this file lean and focused on agent needs.
- Update when the technology stack changes.
- Review quarterly for outdated rules.
- Remove rules that become obvious over time.

Last Updated: 2026-01-08T12:16:26-06:00
