# References for BYOK Config & Endpoint Validation

## Similar Implementations

### Config schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/config.py`
- **Relevance:** Source of truth for run config shape and existing endpoint fields.
- **Key patterns:** `ModelEndpointConfig`, `ModelSettings`, `RunConfig`.

### Config validation entrypoints
- **Location:** `packages/rentl-schemas/src/rentl_schemas/validation.py`
- **Relevance:** Validation entrypoint used by CLI and other surfaces.
- **Key patterns:** `validate_run_config`.

### CLI config loading + API key check
- **Location:** `services/rentl-cli/src/rentl_cli/main.py`
- **Relevance:** Current config loading, path resolution, and API key validation flow.
- **Key patterns:** `_load_run_config`, `_ensure_api_key`.

### CLI unit tests
- **Location:** `tests/unit/cli/test_main.py`
- **Relevance:** CLI testing patterns, TOML config fixtures, JSON envelope assertions.
- **Key patterns:** Typer runner usage, config helpers.

### Schema unit tests
- **Location:** `tests/unit/schemas/test_config.py`
- **Relevance:** Existing schema validation tests and style.
- **Key patterns:** `PipelineConfig` and validator assertions.
