# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): PASS — CHANGELOG includes all completed v0.1 roadmap specs and satisfies task acceptance criteria.
- **Task 3** (round 1): FAIL — `docs/getting-started.md` Step 3 uses `OPENROUTER_API_KEY` and GNU-only `sed -i`, but init-generated projects use `RENTL_LOCAL_API_KEY`; setup instructions are not copy-pasteable on a fresh machine.
- **Task 3** (round 2): PASS — Step 3 now documents the actual init-generated `RENTL_LOCAL_API_KEY` variable and removes GNU-only `sed -i`; CLI command references in the guide match current `rentl` help output.
- **Task 4** (round 1): FAIL — `docs/architecture.md` includes stale architecture references (package inventory/dependency statements, storage-path layout, and BYOK config snippet) that do not match current code and config schema.
- **Task 4** (round 2): FAIL — `docs/architecture.md` still misstates artifact index location (`.rentl/artifacts/{run_id}/index.jsonl`), but code stores a global index at `.rentl/artifacts/index.jsonl`.
- **Task 4** (round 3): PASS — `docs/architecture.md` now correctly documents the global artifact index at `.rentl/artifacts/index.jsonl`, matching `FileSystemArtifactStore` behavior.
- **Task 5** (round 1): PASS — `docs/data-schemas.md` covers the required schema surfaces, and documented fields/types align with `rentl-schemas` model definitions with example JSONL lines matching `samples/golden/artifacts/`.
