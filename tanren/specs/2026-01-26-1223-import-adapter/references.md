# References for Import Adapter (CSV/JSONL/TXT)

## Similar Implementations

### SourceLine schema
- **Location:** `packages/rentl-schemas/src/rentl_schemas/io.py`
- **Relevance:** Target output for all import adapters
- **Key patterns:** Pydantic validation and field requirements

### Phase input usage
- **Location:** `packages/rentl-schemas/src/rentl_schemas/phases.py`
- **Relevance:** Downstream consumers of `SourceLine` in phase inputs
- **Key patterns:** `source_lines` lists with required min_length and strict schema use

### Core primitives
- **Location:** `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- **Relevance:** `LineId`, `SceneId`, `FileFormat` validation patterns
- **Key patterns:** strict regex patterns for IDs and format enums
