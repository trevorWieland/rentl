# CLI Workflow & Phase Selection - Shaping Notes

## Scope
- Add CLI commands to run a full pipeline plan or a single phase with clear status output.
- Wire filesystem-backed run state, artifacts, logs, and progress sinks into CLI runs.
- Load and validate TOML config, resolve paths, and surface structured error envelopes.
- Keep CLI as a thin adapter over core orchestration and storage protocols.

## Decisions
- Use spec 11 baseline scope (full plan + single phase execution, status output, storage wiring).
- No visuals for this spec.
- Align strictly with product mission/roadmap/tech stack.
- Reference existing CLI, core orchestrator, and storage/log/progress adapters.

## Context
- **Visuals:** None
- **References:**
  - `services/rentl-cli/src/rentl_cli/main.py`
  - `tests/unit/cli/test_main.py`
  - `packages/rentl-core/src/rentl_core/orchestrator.py`
  - `packages/rentl-core/src/rentl_core/ports/orchestrator.py`
  - `packages/rentl-core/src/rentl_core/ports/storage.py`
  - `packages/rentl-io/src/rentl_io/storage/filesystem.py`
  - `packages/rentl-io/src/rentl_io/storage/log_sink.py`
  - `packages/rentl-io/src/rentl_io/storage/progress_sink.py`
  - `packages/rentl-io/src/rentl_io/ingest/router.py`
  - `packages/rentl-io/src/rentl_io/export/router.py`
  - `packages/rentl-schemas/src/rentl_schemas/config.py`
  - `packages/rentl-schemas/src/rentl_schemas/validation.py`
  - `packages/rentl-schemas/src/rentl_schemas/storage.py`
  - `packages/rentl-schemas/src/rentl_schemas/io.py`
  - `packages/rentl-schemas/src/rentl_schemas/responses.py`
- **Product alignment:** v0.1 CLI-first, deterministic phase pipeline, transparent progress/observability, BYOK endpoints, TOML config, JSON envelope outputs.

## Standards Applied
- testing/make-all-gate — Verification required before completion
- architecture/thin-adapter-pattern — CLI stays a thin adapter
- architecture/adapter-interface-protocol — Use core protocols for storage/IO
- architecture/log-line-format — JSONL log format preserved
- architecture/api-response-format — CLI outputs use `{data, error, meta}`
- architecture/naming-conventions — CLI commands in kebab-case
- architecture/none-vs-empty — Optional list semantics preserved
- architecture/id-formats — UUIDv7 for run identifiers
- python/async-first-design — Async orchestration with sync CLI entrypoints
- python/pydantic-only-schemas — No dataclasses for schemas
- python/strict-typing-enforcement — No Any/object
- ux/progress-is-product — Clear status output
- ux/trust-through-transparency — No silent failures/stalls
- ux/frictionless-by-default — Safe defaults, guided outputs
- ux/speed-with-guardrails — Determinism and guardrails preserved
