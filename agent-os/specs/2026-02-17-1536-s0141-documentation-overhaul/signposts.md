# Signposts

---

## Signpost 1: PhaseOutput `phase` field documented as required but has default value

- **Task:** Task 5 (Data Schema reference) / Demo Step 4
- **Status:** unresolved
- **Problem:** All 5 PhaseOutput models (`ContextPhaseOutput`, `PretranslationPhaseOutput`, `TranslatePhaseOutput`, `QaPhaseOutput`, `EditPhaseOutput`) document the `phase` field as `required: yes`, but in the actual Pydantic models the field has a constant default (e.g., `Field(PhaseName.CONTEXT, ...)`), making it optional in construction terms.
- **Evidence:**
  - `docs/data-schemas.md:111` — `| phase | PhaseName | yes | Always "context" |`
  - `docs/data-schemas.md:136` — `| phase | PhaseName | yes | Always "pretranslation" |`
  - `docs/data-schemas.md:162` — `| phase | PhaseName | yes | Always "translate" |`
  - `docs/data-schemas.md:187` — `| phase | PhaseName | yes | Always "qa" |`
  - `docs/data-schemas.md:216` — `| phase | PhaseName | yes | Always "edit" |`
  - `packages/rentl-schemas/src/rentl_schemas/phases.py:220` — `phase: PhaseName = Field(PhaseName.CONTEXT, ...)`
  - `packages/rentl-schemas/src/rentl_schemas/phases.py:253` — `phase: PhaseName = Field(PhaseName.PRETRANSLATION, ...)`
  - `packages/rentl-schemas/src/rentl_schemas/phases.py:289` — `phase: PhaseName = Field(PhaseName.TRANSLATE, ...)`
  - `packages/rentl-schemas/src/rentl_schemas/phases.py:320` — `phase: PhaseName = Field(PhaseName.QA, ...)`
  - `packages/rentl-schemas/src/rentl_schemas/phases.py:357` — `phase: PhaseName = Field(PhaseName.EDIT, ...)`
- **Root cause:** When the schema reference was written, the `phase` field was documented by its semantic intent (always present in output) rather than its Pydantic construction requirement (has a default value, so not required for construction).
- **Files affected:** `docs/data-schemas.md` lines 111, 136, 162, 187, 216

---

## Signpost 2: `RequestId` primitive type not documented

- **Task:** Task 5 (Data Schema reference) / Demo Step 4
- **Status:** unresolved
- **Problem:** The `RequestId` type alias (`Uuid7`) is exported from `rentl_schemas.__init__.py` and used in `MetaInfo.request_id` (responses.py), but it is not listed in the Primitive Types table in `docs/data-schemas.md`.
- **Evidence:**
  - `packages/rentl-schemas/src/rentl_schemas/primitives.py:47` — `type RequestId = Uuid7`
  - `packages/rentl-schemas/src/rentl_schemas/__init__.py:133` — `RequestId,` (exported)
  - `packages/rentl-schemas/src/rentl_schemas/__init__.py:360` — `"RequestId",` (in `__all__`)
  - `docs/data-schemas.md:12-30` — Primitive Types table lists 12 types but omits `RequestId`
- **Root cause:** `RequestId` was likely overlooked because it's only used in the API response envelope (`responses.py`), not in the core pipeline data flow models.
- **Files affected:** `docs/data-schemas.md` Primitive Types table (around line 12-30)
