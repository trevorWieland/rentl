# References for BYOK Runtime Integration

## Similar Implementations

### BYOK Config and Endpoint Validation

- **Location:** `agent-os/specs/2026-01-27-1520-byok-config-endpoint-validation/shape.md`
- **Relevance:** Defines endpoint config schema, validation rules, and endpoint resolution precedence.
- **Key patterns:** Endpoint selection (agent -> phase -> default), no provider allowlist.

### Config Schema and Validation

- **Location:** `packages/rentl-schemas/src/rentl_schemas/config.py`
- **Relevance:** Source of endpoint config, retry config, and endpoint resolution helper.
- **Key patterns:** Pydantic Field usage and validation rules.

### Config Validation Entrypoint

- **Location:** `packages/rentl-schemas/src/rentl_schemas/validation.py`
- **Relevance:** Central config validation path used by CLI.

### CLI Run Pipeline Flow

- **Location:** `services/rentl-cli/src/rentl_cli/main.py`
- **Relevance:** Thin adapter structure and current config wiring.

### Endpoint Validation Tests

- **Location:** `tests/unit/schemas/test_config.py`
- **Relevance:** Tests for endpoint config validation behavior.

### CLI Config Error Tests

- **Location:** `tests/unit/cli/test_main.py`
- **Relevance:** CLI error envelope patterns and config error expectations.
