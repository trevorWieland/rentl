# CLI Workflow & Phase Selection Plan

## Goal
- Deliver CLI commands to run a full pipeline plan or a single phase with clear status output.
- Wire filesystem-backed run state, artifacts, logs, and progress sinks into CLI runs.
- Keep CLI as a thin adapter over core orchestration with strict schema validation.
- Align outputs with `{data, error, meta}` envelopes for predictable automation.
- Enable follow-on specs (21 CLI status viewer, 22 onboarding, 23+ agent roster) without rework.

## Execution Note
- Execute Task 1 now, then continue with implementation tasks.

## Task 1: Save Spec Documentation
- Create this spec folder with plan, shape, standards, references, and visuals.

## Task 2: Define CLI workflow + phase selection semantics
- Specify CLI commands and options (`run-pipeline`, `run-phase`, `--config`, `--phase`, `--run-id`, `--target-language`, `--output-path`, `--format`).
- Define run-id behavior (new run generates UUIDv7, `--run-id` resumes from stored state).
- Establish how phases are selected for `run-pipeline` (config order, enabled only) and `run-phase` (single explicit phase).
- Define how export targets are resolved (per-language output naming, format derived from config unless overridden).
- Document status output contract for CLI (success and error envelopes, key fields).

## Task 3: Config loading and validation
- Add a TOML config loader in CLI that resolves relative paths against `workspace_dir`.
- Validate config using `rentl_schemas.validation.validate_run_config` and surface structured errors.
- Ensure API key env var presence is checked with a safe error response (no secret output).

## Task 4: Core wiring helper for CLI runs
- Add a core helper to build a `PipelineOrchestrator` with injected adapters and sinks.
- Ensure ingest/export adapters are wired via router helpers (no direct adapter access).
- Provide a utility to hydrate `PipelineRunContext` from stored run state when resuming.

## Task 5: CLI commands implementation
- Implement `run-pipeline` command:
  - Load config, initialize storage/log/progress sinks from project paths.
  - Create or hydrate run context; run planned phases in order.
  - Emit JSON envelope with run_id, status, progress summary, and artifact/log references.
- Implement `run-phase` command:
  - Load config, build run context (new or resume), execute a single phase.
  - Accept phase-specific flags (ingest source, export target overrides, target language).
  - Emit JSON envelope with phase result summary and updated run state metadata.

## Task 6: Tests (unit)
- Add CLI unit tests for:
  - Successful `run-phase` ingest and persistence outputs.
  - `run-pipeline` fails with missing phase agents (blocked phase response).
  - Config parse/validation errors return structured error envelope.
  - Run state/log/progress artifacts are created at configured paths.

## Task 7: Verification - Run make all
- Run `make all` to ensure format, lint, type, and unit checks pass.
- Fix failures and re-run until green.

## References Studied
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
- `agent-os/specs/2026-01-27-1036-pipeline-orchestrator-core/plan.md`
- `agent-os/specs/2026-01-27-1128-phase-execution-sharding-config/plan.md`
- `agent-os/specs/2026-01-27-1210-phase-history-staleness-rules/plan.md`
- `agent-os/specs/2026-01-27-1304-phase-result-summaries-metrics/plan.md`

## Standards Applied
- architecture/thin-adapter-pattern
- architecture/adapter-interface-protocol
- architecture/log-line-format
- architecture/api-response-format
- architecture/naming-conventions
- architecture/none-vs-empty
- architecture/id-formats
- python/async-first-design
- python/pydantic-only-schemas
- python/strict-typing-enforcement
- ux/progress-is-product
- ux/trust-through-transparency
- ux/frictionless-by-default
- ux/speed-with-guardrails
- testing/make-all-gate

## Product Alignment
- v0.1 requires CLI-first workflow with deterministic phase execution and clear observability.
- Spec 21 (CLI status viewer) depends on storage/log/progress wiring defined here.
- Spec 22 (functional onboarding) depends on predictable CLI behavior and config validation.
- v0.2+ multi-agent specs rely on phase selection and run history being stable.
