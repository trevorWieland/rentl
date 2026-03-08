# References for Export Adapter (CSV/JSONL/TXT)

## Similar Implementations

### Ingest Adapter Ports
- **Location:** `packages/rentl-core/src/rentl_core/ports/ingest.py`
- **Relevance:** Defines adapter protocol, error models, and log events for ingest
- **Key patterns:** Protocol + error enums, error details mapping to response envelope, log event builders

### Ingest Adapters
- **Location:** `packages/rentl-io/src/rentl_io/ingest/`
- **Relevance:** Concrete CSV/JSONL/TXT adapters with router and async IO
- **Key patterns:** `asyncio.to_thread` for IO, format validation, batch error collection, router dispatch

### IO Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/io.py`
- **Relevance:** `ExportTarget` and `TranslatedLine` shapes used by export adapters
- **Key patterns:** Pydantic schema validation and metadata typing

### Phase Output Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/phases.py`
- **Relevance:** `TranslatePhaseOutput` and `EditPhaseOutput` provide translated lines
- **Key patterns:** Field naming consistency and required list fields

### Primitives
- **Location:** `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- **Relevance:** `FileFormat`, `PhaseName`, and type validators for IDs and JSON values
- **Key patterns:** Enforced patterns for IDs and standard enum usage
