status: fail
fix_now_count: 1

# Audit: s0.1.47 Recalibrate Naming Conventions Standard

- Spec: s0.1.47
- Issue: https://github.com/trevorWieland/rentl/issues/134
- Date: 2026-03-09
- Round: 1

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 4/5
- Completion: 4/5
- Security: 5/5
- Stability: 5/5

## Non-Negotiable Compliance
1. Standard drives code, not vice versa: **PASS** — Standard now explicitly requires module-level constants as `SCREAMING_SNAKE_CASE` (`tanren/standards/architecture/naming-conventions.md:47-50`), and constants remain correctly cased in code (`packages/rentl-schemas/src/rentl_schemas/version.py:10`, `packages/rentl-io/src/rentl_io/ingest/csv_adapter.py:21-26`, `packages/rentl-llm/src/rentl_llm/providers.py:37-42`). Independent audit scan found no top-level lowercase constant-like assignments outside known template literals in `init.py`.
2. Internally consistent standard: **PASS** — Case styles are documented without contradiction (`snake_case`, `PascalCase`, and module-level `SCREAMING_SNAKE_CASE`) in one consolidated section (`tanren/standards/architecture/naming-conventions.md:43-50`) with concrete good/bad examples (`tanren/standards/architecture/naming-conventions.md:52-66`).
3. No fabricated examples: **PASS** — Added constant examples map to real repo definitions: `CURRENT_SCHEMA_VERSION` (`packages/rentl-schemas/src/rentl_schemas/version.py:10`), `REQUIRED_COLUMNS` (`packages/rentl-io/src/rentl_io/ingest/csv_adapter.py:21`), `OPENROUTER_CAPABILITIES` fields (`packages/rentl-llm/src/rentl_llm/providers.py:37-42`).

## Demo Status
- Latest run: PASS (Run 2, 2026-03-09)
- Demo [RUN] steps all passed (`tanren/specs/2026-03-06-2355-s0.1.47-naming-conventions-standard/demo.md:32-37`); Step 4 remains intentionally skipped due missing CLI in environment.
- Full verification gate evidence from this audit: `make all` passed (format, lint, type, 1133 unit tests, 103 integration tests, 10 quality tests).

## Standards Adherence
- `architecture/naming-conventions`: PASS — Standard now explicitly includes module-level `SCREAMING_SNAKE_CASE` rule and guidance (`tanren/standards/architecture/naming-conventions.md:47-50`).
- `global/no-placeholder-artifacts`: PASS — Constant examples are real and match implementation (`packages/rentl-schemas/src/rentl_schemas/version.py:10`, `packages/rentl-io/src/rentl_io/ingest/csv_adapter.py:21`, `packages/rentl-llm/src/rentl_llm/providers.py:37-42`).
- `ux/copy-pasteable-examples`: **violation (Medium)** — Demo Step 4 references a non-existent path `./agent-os/scripts/audit-standards.sh` (`tanren/specs/2026-03-06-2355-s0.1.47-naming-conventions-standard/demo.md:19`); actual script path is `./tanren/scripts/audit-standards.sh`.

## Signpost Cross-Reference
- Existing unresolved signpost is for Demo Step 1 path drift (`signposts.md`, “Run Demo Step 1”); that specific problem is resolved in code (`demo.md:13` now uses `tanren/standards/...`) and is not re-opened.
- New Fix Now item targets a different stale path (`demo.md:19`, Step 4), and is routed to existing open Task 7 in `plan.md` to avoid duplicate orphaned fix tracking.

## Regression Check
- Prior repeated failures for missing `SCREAMING_SNAKE_CASE` guidance and fabricated `OPENROUTER_CAPABILITIES` fields have not regressed; current standard and provider constants align.
- Path-drift issue pattern remains: migration from `agent-os` to `tanren` caused stale path references (Demo Run 1 failed on this class of issue, and Step 4 still has the same drift pattern).

## Action Items

### Fix Now
- Update Demo Step 4 command path from `./agent-os/scripts/audit-standards.sh` to `./tanren/scripts/audit-standards.sh` in `tanren/specs/2026-03-06-2355-s0.1.47-naming-conventions-standard/demo.md:19`, then complete Task 7 in `plan.md` (audit round 1).

### Deferred
- None.
