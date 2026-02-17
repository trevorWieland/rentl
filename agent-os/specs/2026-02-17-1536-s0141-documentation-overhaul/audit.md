status: fail
fix_now_count: 2

# Audit: s0.1.41 Documentation Overhaul for v0.1 Release

- Spec: s0.1.41
- Issue: https://github.com/trevorWieland/rentl/issues/125
- Date: 2026-02-17
- Round: 1

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 3/5
- Completion: 3/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. Getting Started guide is copy-pasteable: **FAIL** — `docs/getting-started.md:207` uses `out/run-<run-id>/...` and fails without manual edits (`bash: line 1: run-id: No such file or directory`); `docs/getting-started.md:217` also uses a placeholder command (`--phase <phase>`).
2. Architecture doc matches code: **PASS** — pipeline phase names in `docs/architecture.md:31` match `packages/rentl-schemas/src/rentl_schemas/primitives.py:61`; documented wrapper/build symbols in `docs/architecture.md:145` and `docs/architecture.md:151` exist in `packages/rentl-agents/src/rentl_agents/wiring.py:150` and `packages/rentl-agents/src/rentl_agents/wiring.py:1104`.
3. Schema reference matches Pydantic models: **PASS** — documented fields for `SourceLine`/`TranslatedLine` in `docs/data-schemas.md:58` and `docs/data-schemas.md:75` match model definitions in `packages/rentl-schemas/src/rentl_schemas/io.py:53` and `packages/rentl-schemas/src/rentl_schemas/io.py:69`; prior full field audit recorded pass in `agent-os/specs/2026-02-17-1536-s0141-documentation-overhaul/audit-log.md:14`.
4. No copyrighted text ships in PyPI packages: **PASS** — runtime downloader fetches benchmark text in `packages/rentl-core/src/rentl_core/benchmark/eval_sets/downloader.py:14`; packaged benchmark metadata contains hashes/URLs only (`packages/rentl-core/src/rentl_core/benchmark/eval_sets/katawa_shoujo/manifest.json:2`).
5. CHANGELOG covers all shipped specs: **PASS** — roadmap has 37 completed `s0.1.xx` specs (`agent-os/product/roadmap.md:29`), changelog includes all completed IDs plus explicitly non-included deferred/closed specs (`CHANGELOG.md:74`). Command cross-check found no missing completed IDs.
6. All new docs cross-linked from README: **PASS** — README links all four required docs at `README.md:324`, `README.md:325`, `README.md:326`, and `README.md:327`.

## Demo Status
- Latest run: PASS (Run 1, 2026-02-17)
- Results are not fully convincing: `demo.md:29` claims `run-phase --phase all` exists, but CLI accepts `PhaseName` values only (`services/rentl-cli/src/rentl/main.py:215`, `services/rentl-cli/src/rentl/main.py:1030`).

## Standards Adherence
- `ux/copy-pasteable-examples`: **violation (High)** — placeholder commands in `docs/getting-started.md:207` and `docs/getting-started.md:217` require manual substitution and are not executable as-is.
- `ux/stale-reference-prevention`: **violation (Medium)** — demo result references stale CLI behavior in `demo.md:29` vs current command contract in `services/rentl-cli/src/rentl/main.py:1030`.
- `ux/frictionless-by-default`: **violation (Medium)** — first-run tutorial requires hidden manual edits due placeholder tokens (`docs/getting-started.md:207`).
- `global/no-placeholder-artifacts`: **violation (High)** — unresolved placeholder artifact committed in tutorial command (`docs/getting-started.md:207`).

## Regression Check
- Previously fixed Task 3 and Task 4 issues remain resolved (`agent-os/specs/2026-02-17-1536-s0141-documentation-overhaul/audit-log.md:10`, `agent-os/specs/2026-02-17-1536-s0141-documentation-overhaul/audit-log.md:13`).
- New full-spec audit surfaced gaps not captured in task rounds: copy-pasteability regression in Step 8 of Getting Started and stale CLI reference in demo results.
- `signposts.md` is not present in this spec folder, so no deferred/resolved signpost exceptions applied.

## Action Items

### Fix Now
- Task 3: Replace non-executable placeholder commands with copy-pasteable alternatives (`docs/getting-started.md:207`, `docs/getting-started.md:217`) (High).
- Task 1: Correct and re-verify demo Step 2 command evidence to remove invalid `run-phase --phase all` claim (`demo.md:29`, `services/rentl-cli/src/rentl/main.py:1030`) (Medium).

### Deferred
- None.
