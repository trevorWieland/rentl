# References: Project Bootstrap Command

## Issue
- https://github.com/trevorWieland/rentl/issues/29

## Dependencies
- s0.1.01 — Core pipeline orchestration (completed)
- s0.1.03 — Config schema (completed)
- s0.1.11 — Agent wiring (completed)

## Implementation Files

### Config Schema
- `packages/rentl-schemas/src/rentl_schemas/config.py` — `RunConfig`, `AgentsConfig`, validation
- `packages/rentl-schemas/src/rentl_schemas/primitives.py` — `LanguageCode`, `FileFormat`

### CLI
- `services/rentl-cli/src/rentl_cli/main.py` — CLI commands, config loading, path resolution

### Agent Discovery
- `packages/rentl-agents/src/rentl_agents/wiring.py` — `build_agent_pools()`, `get_default_agents_dir()`, `get_default_prompts_dir()`

### Core (New)
- `packages/rentl-core/src/rentl_core/init.py` — Init interview schema and project generation (to be created)

### Example Config
- `rentl.toml.example` — Reference for generated config structure

### Sample Data
- `samples/style-guide.md` — Style guide example
- `samples/golden/script.jsonl` — Sample JSONL format reference

## Related Specs
- s0.2.20 — Future expansion of init (more options, Copier integration)
