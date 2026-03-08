# References: Recalibrate Naming Conventions Standard

## Issues

- https://github.com/trevorWieland/rentl/issues/134 — s0.1.47 Recalibrate Naming Conventions Standard

## Files Being Modified

- `agent-os/standards/architecture/naming-conventions.md` — standard being updated
- `agent-os/standards/index.yml` — description field update

## Audit Evidence

- `agent-os/audits/2026-02-17/naming-conventions.md` — source audit report; 61 violations, all SCREAMING_SNAKE module-level constants

## Example Violations (all correct Python, flagged by faulty standard)

- `packages/rentl-schemas/src/rentl_schemas/version.py:10` — `CURRENT_SCHEMA_VERSION`
- `packages/rentl-schemas/src/rentl_schemas/primitives.py:11` — `HUMAN_ID_PATTERN`, `ISO_8601_PATTERN`
- `packages/rentl-io/src/rentl_io/ingest/csv_adapter.py:21` — `REQUIRED_COLUMNS`, `OPTIONAL_COLUMNS`
- `packages/rentl-agents/src/rentl_agents/providers.py:32` — `OPENROUTER_CAPABILITIES`

## Related Standards

- PEP 8 — https://peps.python.org/pep-0008/#constants (defines SCREAMING_SNAKE_CASE for module-level constants)
