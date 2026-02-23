# References: Documentation Placeholders, CLI Surface & UX Polish

## Issue
- https://github.com/trevorWieland/rentl/issues/130

## Implementation Files

### Documentation (Task 2)
- `README.md` — placeholder commands, stale env var names
- `CONTRIBUTING.md` — `<spec-folder>`, `<your-spec-folder>` placeholders
- `docs/troubleshooting.md` — `<command>` placeholder
- `WORKFLOW-GUIDE.md` — `<spec-folder>` placeholders
- `agent-os/docs/draft-*.md` — `<spec-folder>` placeholders (26 locations)
- `agent-os/standards/ux/copy-pasteable-examples.md` — hardcoded `run-001`, `<command>` placeholder

### Help Registry & Docstring Gating (Task 3)
- `packages/rentl-core/src/rentl_core/help.py` — command registry
- `services/rentl-cli/src/rentl/main.py:243,260,1200,1351` — docstrings needing `\f` gates

### CLI Extraction (Task 4)
- `services/rentl-cli/src/rentl/main.py:3712` — migrate logic
- `services/rentl-cli/src/rentl/main.py:3574` — check-secrets logic
- `services/rentl-cli/src/rentl/main.py:3910` — TOML serialization
- New: `packages/rentl-core/src/rentl_core/migrate.py`
- New: `packages/rentl-core/src/rentl_core/secrets.py`
- New: `packages/rentl-core/src/rentl_core/config/serialization.py`

### Init UX (Task 5)
- `services/rentl-cli/src/rentl/main.py:569,574,666` — init command
- `packages/rentl-core/src/rentl_core/init.py:124,260` — config generation

### Observability (Task 6)
- `services/rentl-cli/src/rentl/main.py:936,1038-1085,1832-1834,3137` — progress and error context
- `packages/rentl-core/src/rentl_core/llm/connection.py:198` — retry visibility
- `packages/rentl-core/src/rentl_core/orchestrator.py:564-621,1083-1172` — ingest/export progress

## Audit Reports
- `agent-os/audits/2026-02-17/`

## Standards Files
- `agent-os/standards/ux/copy-pasteable-examples.md`
- `agent-os/standards/ux/stale-reference-prevention.md`
- `agent-os/standards/ux/frictionless-by-default.md`
- `agent-os/standards/architecture/thin-adapter-pattern.md`
- `agent-os/standards/python/cli-help-docstring-gating.md`
- `agent-os/standards/ux/trust-through-transparency.md`
- `agent-os/standards/ux/progress-is-product.md`
