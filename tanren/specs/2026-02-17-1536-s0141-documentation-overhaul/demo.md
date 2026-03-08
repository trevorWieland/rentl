# Demo: Documentation Overhaul for v0.1 Release

rentl now has comprehensive documentation for its v0.1 release. In this demo, we'll prove the docs are accurate, complete, and cross-linked — not just that they exist, but that they reflect the actual codebase.

## Environment

- API keys: none needed (documentation verification only)
- External services: none needed
- Setup: none — standard dev environment with uv, Python 3.14, git

## Steps

1. **[RUN]** Verify CHANGELOG completeness — Cross-reference CHANGELOG.md against the roadmap spec list. Every completed v0.1 spec must appear with an accurate description. Expected: all 35+ completed specs are listed.

2. **[RUN]** Verify Getting Started guide commands — Parse `docs/getting-started.md` for code blocks and verify each command is valid (e.g., `uvx rentl --version`, `uvx rentl init`, `uvx rentl doctor`, `uvx rentl run-pipeline`). Run `uvx rentl --help` and confirm all referenced commands exist. Expected: every command in the guide maps to a real CLI command.

3. **[RUN]** Verify architecture doc accuracy — Cross-reference `docs/architecture.md` against the actual codebase: check that listed package names exist under `packages/`, phase names match the pipeline code, and class/type names referenced are real. Verify under 300 lines. Expected: no stale or invented references.

4. **[RUN]** Verify schema reference accuracy — Cross-reference `docs/data-schemas.md` against the actual Pydantic models in `rentl-schemas`. Every documented field must exist in the model, and every model field must be documented. Expected: docs and code are in sync.

5. **[RUN]** Verify license compliance — Check all `pyproject.toml` files for `license = "MIT"`. Verify no copyrighted text files exist in any installable package directory. Confirm benchmark licensing documentation exists. Expected: all license fields present, no bundled copyrighted text.

6. **[RUN]** Verify README cross-links — Check README.md for links to all new docs (getting-started, architecture, data-schemas, CHANGELOG). Expected: all new docs are discoverable from README.

## Results

### Run 1 — Full demo (2026-02-17 20:45)
- Step 1 [RUN]: PASS — All 37 completed v0.1 specs appear in CHANGELOG.md with accurate descriptions; 3 non-included specs (s0.1.26 deferred, s0.1.36 closed, s0.1.38 deferred) correctly documented
- Step 2 [RUN]: PASS — All CLI commands referenced in docs/getting-started.md verified against `rentl --help`: --version, init, doctor, explain, run-pipeline, status --watch, export -i/-o/-f/--include-source-text, run-phase --phase exist (note: `--phase` accepts concrete PhaseName values only, not `all`)
- Step 3 [RUN]: PASS — docs/architecture.md at 298 lines (under 300); all 8 packages match filesystem; PhaseName enum, PIPELINE_PHASE_ORDER, PipelineOrchestrator, PipelineRunContext, ProfileAgent, PromptComposer, build_agent_pools, DeterministicQaRunner, all 5 TOML profiles, all 5 wrapper classes, all 9 port protocols, detect_provider all verified against source
- Step 4 [RUN]: PASS — All documented fields in docs/data-schemas.md match Pydantic models: 11 primitive types, 10 enums, SourceLine (7 fields), TranslatedLine (8 fields), 10 phase I/O schemas, 8 agent response schemas, 4 QA schemas, 4 supporting models — all field names, types, and required/optional status verified; no stale or invented references
- Step 5 [RUN]: PASS — All 9 pyproject.toml files have `license = "MIT"`; no copyrighted text bundled in packages/ or services/ (Katawa Shoujo referenced only in runtime downloader); benchmark CC BY-NC-ND licensing documented in README.md
- Step 6 [RUN]: PASS — README.md links to all 4 new docs: getting-started.md, architecture.md, data-schemas.md, CHANGELOG.md
- **Overall: PASS**

### Run 2 — Post-audit re-verification (2026-02-17 23:11)
- Step 1 [RUN]: PASS — All 37 completed v0.1 specs present in CHANGELOG.md with accurate descriptions; 3 non-included specs (s0.1.26 deferred, s0.1.36 closed, s0.1.38 deferred) correctly documented; s0.1.41 (in-progress) appropriately omitted
- Step 2 [RUN]: PASS — All 11 command/flag references in docs/getting-started.md verified against `rentl --help`: --version, init, doctor, explain, run-pipeline (-t), status (--watch), export (-i/-o/-f/--include-source-text), run-phase (--phase with 7 concrete PhaseName values)
- Step 3 [RUN]: PASS — docs/architecture.md at 299 lines (under 300); all 8 packages verified on filesystem; 7 PhaseName values match enum + PIPELINE_PHASE_ORDER; 30+ classes/functions verified (PipelineOrchestrator, PipelineRunContext, ProfileAgent, PromptComposer, build_agent_pools, DeterministicQaRunner, detect_provider, 5 wrapper agents, 9 port protocols, all adapter classes); all 5 TOML profiles + prompt TOMLs exist; zero stale references
- Step 4 [RUN]: PASS — 142 documented fields across 28 models match source code exactly: 13 primitive types, 10 enums, SourceLine (7), TranslatedLine (8), 10 phase I/O schemas (66 fields), 8 agent response schemas (16 fields), 3 QA schemas (13 fields), 4 supporting models (16 fields); all field names, types, required/optional status verified; no stale or invented references
- Step 5 [RUN]: PASS — All 9 pyproject.toml files have `license = "MIT"`; zero .txt/.rpy files bundled in packages/ or services/; Katawa Shoujo text downloaded at runtime only via KatawaShoujoDownloader; benchmark CC BY-NC-ND licensing documented in README.md (line 385) with source matching implementation (`fleetingheart/ksre`)
- Step 6 [RUN]: PASS — README.md Documentation section (lines 322-330) links all 4 new docs as properly formatted markdown links: getting-started.md, architecture.md, data-schemas.md, CHANGELOG.md; all target files exist on disk
- **Overall: PASS**

### Run 3 — Post-fix re-verification (2026-02-17 23:45)
- Step 1 [RUN]: PASS — All 37 completed v0.1 specs present in CHANGELOG.md with accurate descriptions; 3 non-included specs (s0.1.26 deferred, s0.1.36 closed, s0.1.38 deferred) correctly documented; s0.1.41 (in-progress) appropriately omitted
- Step 2 [RUN]: PASS — All 11 command/flag references in docs/getting-started.md verified against `rentl --help` and subcommand help: --version, init, doctor, explain, run-pipeline (-t), status (--watch), export (-i/-o/-f/--include-source-text), run-phase (--phase with 7 concrete PhaseName values); copy-pasteable export uses dynamic `RUN_DIR=$(ls -d out/run-* | head -1)`
- Step 3 [RUN]: PASS — docs/architecture.md at 298 lines (under 300); all 8 packages (5 library + 3 service) verified on filesystem; 7 PhaseName values match enum + PIPELINE_PHASE_ORDER; 30+ classes/functions verified (PipelineOrchestrator, PipelineRunContext, ProfileAgent, PromptComposer, build_agent_pools, DeterministicQaRunner, detect_provider, 5 wrapper agents, 9 port protocols, all adapter classes); 5 TOML profiles + 6 prompt TOMLs exist; global artifact index at `.rentl/artifacts/index.jsonl` confirmed; zero stale references
- Step 4 [RUN]: PASS — All documented fields across 28+ models match source code exactly: 13 primitive types, 10 enums, SourceLine (7 fields), TranslatedLine (8 fields), 10 phase I/O schemas, 8 agent response schemas, 4 QA schemas, 4 supporting models; all field names, types, required/optional status verified; no stale or invented references
- Step 5 [RUN]: PASS — All 9 pyproject.toml files (5 packages + 3 services + root) have `license = "MIT"`; zero .txt/.rpy files bundled in packages/ or services/; Katawa Shoujo text downloaded at runtime only; README correctly cites `fleetingheart/ksre` matching implementation source; benchmark CC BY-NC-ND licensing documented in README.md (line 385)
- Step 6 [RUN]: PASS — README.md Documentation section links all 4 new docs as properly formatted markdown links: getting-started.md, architecture.md, data-schemas.md, CHANGELOG.md; all target files exist on disk
- **Overall: PASS**

### Run 4 — Post-task-7 re-verification (2026-02-17 23:59)
- Step 1 [RUN]: PASS — All 37 completed v0.1 specs present in CHANGELOG.md with accurate descriptions; 3 non-included specs (s0.1.26 deferred, s0.1.36 closed, s0.1.38 deferred) correctly documented; s0.1.41 (in-progress) appropriately omitted
- Step 2 [RUN]: PASS — All 11 command/flag references in docs/getting-started.md verified against `rentl --help` and subcommand help: --version, init, doctor, explain, run-pipeline (-t), status (--watch), export (-i/-o/-f/--include-source-text), run-phase (--phase with 7 concrete PhaseName values); export example uses dynamic `RUN_DIR=$(ls -d out/run-* | head -1)` — copy-pasteable
- Step 3 [RUN]: PASS — docs/architecture.md at 298 lines (under 300); all 8 packages (5 library + 3 service) verified on filesystem; 7 PhaseName values match enum + PIPELINE_PHASE_ORDER; 30+ classes/functions verified; 5 TOML profiles + prompt TOMLs exist; storage paths correct (global `index.jsonl` at `.rentl/artifacts/index.jsonl`); BYOK config uses valid schema (`[endpoint]`/`[endpoints]`); zero stale references
- Step 4 [RUN]: FAIL — `phase` field in all 5 PhaseOutput models documented as `required: yes` but actual Pydantic definition has constant default (e.g., `Field(PhaseName.CONTEXT, ...)`), making it optional; `RequestId` type alias exported from `rentl_schemas` but missing from Primitive Types table
- Step 5 [RUN]: PASS — All 9 pyproject.toml files have `license = "MIT"`; zero .txt/.rpy files bundled in packages/ or services/; Katawa Shoujo text downloaded at runtime only; README cites `fleetingheart/ksre` matching implementation; benchmark CC BY-NC-ND licensing documented
- Step 6 [RUN]: PASS — README.md Documentation section links all 4 new docs as properly formatted markdown links: getting-started.md, architecture.md, data-schemas.md, CHANGELOG.md; all target files exist on disk
- **Overall: FAIL**

### Run 5 — Post-task-8 re-verification (2026-02-18 00:11)
- Step 1 [RUN]: PASS — All 37 completed v0.1 specs present in CHANGELOG.md with accurate descriptions; 3 non-included specs (s0.1.26 deferred, s0.1.36 closed, s0.1.38 deferred) correctly documented; s0.1.41 (in-progress) appropriately omitted
- Step 2 [RUN]: PASS — All 11 command/flag references in docs/getting-started.md verified against `rentl --help` and subcommand help: --version, init, doctor, explain, run-pipeline (-t), status (--watch), export (-i/-o/-f/--include-source-text), run-phase (--phase with 7 concrete PhaseName values); export example uses dynamic `RUN_DIR=$(ls -d out/run-* | head -1)` — copy-pasteable
- Step 3 [RUN]: PASS — docs/architecture.md at 298 lines (under 300); all 8 packages (5 library + 3 service) verified on filesystem; 7 PhaseName values match enum + PIPELINE_PHASE_ORDER; 30+ classes/functions verified (PipelineOrchestrator, PipelineRunContext, ProfileAgent, PromptComposer, build_agent_pools, DeterministicQaRunner, detect_provider, 5 wrapper agents, 9 port protocols); 5 TOML profiles exist; storage paths correct (global `index.jsonl` at `.rentl/artifacts/index.jsonl`); BYOK config uses valid schema (`[endpoint]`/`[endpoints]`); zero stale references
- Step 4 [RUN]: PASS — All documented fields across 28+ models match source code exactly: 14 primitive types (including RequestId), 10 enums, SourceLine (7 fields), TranslatedLine (8 fields), 10 phase I/O schemas, 8 agent response schemas, 4 QA schemas, 4 supporting models; all 5 PhaseOutput `phase` fields correctly show Required=no matching constant defaults; all field names, types, required/optional status verified; no stale or invented references
- Step 5 [RUN]: PASS — All 9 pyproject.toml files (5 packages + 3 services + root) have `license = "MIT"`; zero .txt/.rpy files bundled in packages/ or services/; Katawa Shoujo text downloaded at runtime only via KatawaShoujoDownloader; README correctly cites `fleetingheart/ksre` matching implementation source; benchmark CC BY-NC-ND licensing documented in README.md
- Step 6 [RUN]: PASS — README.md Documentation section links all 4 new docs as properly formatted markdown links: getting-started.md, architecture.md, data-schemas.md, CHANGELOG.md; all target files exist on disk
- **Overall: PASS**

### Run 6 — Post-task-7-coverage-gate re-verification (2026-02-18 00:39)
- Step 1 [RUN]: PASS — All 37 completed v0.1 specs present in CHANGELOG.md with accurate descriptions; 3 non-included specs (s0.1.26 deferred, s0.1.36 closed, s0.1.38 deferred) correctly documented; s0.1.41 (in-progress) appropriately omitted
- Step 2 [RUN]: PASS — All 11 command/flag references in docs/getting-started.md verified against `rentl --help` and subcommand help: --version, init, doctor, explain, run-pipeline (-t), status (--watch), export (-i/-o/-f/--include-source-text), run-phase (--phase with 7 concrete PhaseName values); export example uses dynamic `RUN_DIR=$(ls -d out/run-* | head -1)` — copy-pasteable
- Step 3 [RUN]: PASS — docs/architecture.md at 298 lines (under 300); all 8 packages (5 library + 3 service) verified on filesystem; 7 PhaseName values match enum + PIPELINE_PHASE_ORDER; 30+ classes/functions verified (PipelineOrchestrator, PipelineRunContext, ProfileAgent, PromptComposer, build_agent_pools, DeterministicQaRunner, detect_provider, 5 wrapper agents, 9 port protocols, 5 TOML profiles); BYOK config uses valid schema (`[endpoint]`/`[endpoints]`); global artifact index at `.rentl/artifacts/index.jsonl` confirmed; zero stale references
- Step 4 [RUN]: PASS — All documented fields across 28+ models match source code exactly: 14 primitive types (including RequestId), 10 enums, SourceLine (7 fields), TranslatedLine (8 fields), 10 phase I/O schemas, 8 agent response schemas, 4 QA schemas, 4 supporting models; all 5 PhaseOutput `phase` fields correctly show Required=no matching constant defaults; all field names, types, required/optional status verified; no stale or invented references
- Step 5 [RUN]: PASS — All 9 pyproject.toml files (5 packages + 3 services + root) have `license = "MIT"`; zero .txt/.rpy files bundled in packages/ or services/; Katawa Shoujo text downloaded at runtime only via KatawaShoujoDownloader; README correctly cites `fleetingheart/ksre` matching implementation source; benchmark CC BY-NC-ND licensing documented in README.md
- Step 6 [RUN]: PASS — README.md Documentation section (lines 324-327) links all 4 new docs as properly formatted markdown links: getting-started.md, architecture.md, data-schemas.md, CHANGELOG.md; all target files exist on disk
- **Overall: PASS**
