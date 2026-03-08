# References: Documentation Overhaul for v0.1 Release

## Issue
- https://github.com/trevorWieland/rentl/issues/125

## Dependencies
- s0.1.39 — Install Verification (uvx/uv tool)
- s0.1.30 — Onboarding Docs Pack

## Implementation Files
- `CHANGELOG.md` — v0.1 release notes (new)
- `docs/getting-started.md` — Getting Started guide (new)
- `docs/architecture.md` — Architecture overview (new)
- `docs/data-schemas.md` — Data schema reference (new)
- `README.md` — Cross-links to new docs (modify)
- `**/pyproject.toml` — License field additions (modify)

## Reference Files
- `agent-os/product/roadmap.md` — Spec list for CHANGELOG
- `README.md` — Existing quick start and project structure
- `docs/quality-evals.md` — Existing doc style reference
- `docs/troubleshooting.md` — Existing doc style reference
- `docs/progress-tracking.md` — Existing doc style reference
- `packages/rentl-schemas/` — Pydantic model definitions for schema reference
- `samples/golden/artifacts/` — Example JSONL for schema reference
- `packages/rentl-core/` — Pipeline orchestrator and phase execution
- `packages/rentl-agents/` — Agent runtime, TOML profiles, prompts
- `packages/rentl-llm/` — LLM integration layer
- `packages/rentl-io/` — I/O adapters
- `packages/rentl-tui/` — TUI package
- `services/rentl-cli/` — CLI application

## Related Specs
- s0.1.30 — Onboarding Docs Pack (existing docs created here)
- s0.1.22 — Functional Onboarding (init, doctor, explain)
- s0.1.32 — Sample Project + Golden Artifacts
- s0.1.37 — Benchmark Harness v0.1
