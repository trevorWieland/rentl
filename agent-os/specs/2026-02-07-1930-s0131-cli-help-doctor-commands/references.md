# References: CLI Help/Doctor Commands

## Implementation Files

### CLI Entry Point
- `services/rentl-cli/src/rentl_cli/main.py` — Existing CLI with Typer app, all current commands

### Core Modules (to create)
- `packages/rentl-core/src/rentl_core/doctor.py` — Doctor diagnostics logic
- `packages/rentl-core/src/rentl_core/explain.py` — Phase explainer logic
- `packages/rentl-core/src/rentl_core/help.py` — Help content logic

### Existing Core References
- `packages/rentl-core/src/rentl_core/llm/connection.py` — `validate_connections()` for LLM connectivity checks
- `packages/rentl-core/src/rentl_core/init.py` — Project initialization (referenced by doctor for workspace validation)
- `packages/rentl-core/src/rentl_core/status.py` — Status reporting patterns

### Schema References
- `packages/rentl-schemas/src/rentl_schemas/primitives.py` — `PhaseName` enum, `PIPELINE_PHASE_ORDER`
- `packages/rentl-schemas/src/rentl_schemas/exit_codes.py` — `ExitCode` enum, exit code taxonomy
- `packages/rentl-schemas/src/rentl_schemas/config.py` — `RunConfig` for config validation

### Config
- `rentl.toml.example` — Example config file structure

## Issues
- https://github.com/trevorWieland/rentl/issues/31

## Dependencies (completed)
- s0.1.06 — Config schema (provides `RunConfig` for doctor validation)
- s0.1.11 — Phase orchestration (provides pipeline structure for explain)
- s0.1.12 — CLI entry point (provides existing command structure for help)
