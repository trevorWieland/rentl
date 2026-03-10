# Demo: Recalibrate Naming Conventions Standard

The naming-conventions standard incorrectly flagged 61 valid Python constants as violations. After this fix, the standard correctly documents PEP 8 — `SCREAMING_SNAKE_CASE` for module-level constants — proving the standard is now right and the code always was.

## Environment

- API keys: none required
- External services: none
- Setup: none — all steps operate on local files and grep

## Steps

1. **[RUN]** Show that `naming-conventions.md` now contains an explicit `SCREAMING_SNAKE_CASE` rule — `grep -i "SCREAMING_SNAKE" agent-os/standards/architecture/naming-conventions.md` should return at least one line
2. **[RUN]** Confirm three previously-flagged constants exist in the codebase and match the updated standard:
   - `grep -r "CURRENT_SCHEMA_VERSION" packages/rentl-schemas/`
   - `grep -r "REQUIRED_COLUMNS" packages/rentl-io/`
   - `grep -r "OPENROUTER_CAPABILITIES" packages/rentl-agents/`
3. **[RUN]** Run `make check` to confirm all unit tests pass with no regressions from any constant renames
4. **[SKIP]** Run `./agent-os/scripts/audit-standards.sh --standards naming-conventions` and verify improved score — `codex exec` CLI not available in this container (not reachable during shaping)

## Results

(Appended by run-demo — do not write this section during shaping)

### Run 1 — Initial demo execution (2026-03-09 22:28)
- Step 1 [RUN]: FAIL — File path `agent-os/standards/architecture/naming-conventions.md` does not exist. Actual file is at `tanren/standards/architecture/naming-conventions.md`. Path needs updating in demo.md.
- Step 2 [RUN]: NOT EXECUTED — Stopped after Step 1 failure
- Step 3 [RUN]: NOT EXECUTED — Stopped after Step 1 failure
- Step 4 [SKIP]: SKIPPED — codex CLI not available
- **Overall: FAIL**
