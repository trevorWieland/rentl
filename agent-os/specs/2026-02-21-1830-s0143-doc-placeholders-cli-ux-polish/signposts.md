# Signposts

Errors, dead ends, and non-obvious solutions encountered during implementation/audit.
Read this before starting any task to avoid repeating known issues.

**Rule: every signpost must include evidence.**

---

## Signpost 1: Placeholder replacement introduced non-executable orchestrator examples

- **Task:** Task 2 (audit round 1)
- **Status:** unresolved
- **Problem:** `<spec-folder>` placeholders were replaced with a hardcoded path that does not exist in the repo, so documented orchestrator commands fail.
- **Evidence:** `agent-os/docs/WORKFLOW-GUIDE.md:139`, `agent-os/docs/draft-complete.md:133`, `agent-os/docs/draft-concise.md:78`, `agent-os/docs/draft-educational.md:139`, `agent-os/docs/draft-general.md:206` all use `agent-os/specs/2026-02-15-1400-s0142-feature-name`.
- **Evidence:** Running the documented command fails:
  ```bash
  $ ./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-15-1400-s0142-feature-name
  [orch] spec.md not found in agent-os/specs/2026-02-15-1400-s0142-feature-name
  ```
- **Impact:** Violates `ux/copy-pasteable-examples` ("executable without modification") and reintroduces stale-reference risk in onboarding docs.
