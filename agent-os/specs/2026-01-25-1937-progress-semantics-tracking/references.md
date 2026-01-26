# References for Progress Semantics & Tracking

## Similar Implementations

### Pydantic Schemas and Validation Spec
- **Location:** `agent-os/specs/2026-01-25-1200-pydantic-schemas-validation/`
- **Relevance:** Established schema layout and validation conventions for v0.1
- **Key patterns:** Strict Pydantic models, shared primitives, pipeline state in `rentl-schemas`

### Pipeline Run State Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/pipeline.py`
- **Relevance:** Current progress models (`PhaseProgress`, `RunProgress`) to extend
- **Key patterns:** Run metadata, phase status, schema-level validation

### Phase IO Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/phases.py`
- **Relevance:** Phase outputs define the unit types we can track (lines, scenes, issues)
- **Key patterns:** Phase-specific payloads and IDs

### IO Primitives
- **Location:** `packages/rentl-schemas/src/rentl_schemas/io.py`
- **Relevance:** Source/translated line shapes for line-based progress
- **Key patterns:** Line and scene identifiers, metadata fields

### QA Schemas
- **Location:** `packages/rentl-schemas/src/rentl_schemas/qa.py`
- **Relevance:** Issue counts and QA summaries for QA phase metrics
- **Key patterns:** Issue severity/category summaries

### Shared Primitives
- **Location:** `packages/rentl-schemas/src/rentl_schemas/primitives.py`
- **Relevance:** Enums and primitive types for progress enums and IDs
- **Key patterns:** Phase names, status enums, ID formats

### Validation Helpers
- **Location:** `packages/rentl-schemas/src/rentl_schemas/validation.py`
- **Relevance:** Place to add progress-specific validation helpers
- **Key patterns:** Centralized validation entrypoints
