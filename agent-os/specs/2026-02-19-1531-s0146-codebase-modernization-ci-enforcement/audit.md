status: fail
fix_now_count: 2

# Audit: s0.1.46 Codebase Modernization & CI Enforcement

- Spec: s0.1.46
- Issue: https://github.com/trevorWieland/rentl/issues/133
- Date: 2026-02-20
- Round: 2

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 4/5
- Completion: 3/5
- Security: 5/5
- Stability: 3/5

## Non-Negotiable Compliance
1. Zero dataclasses remain in production code: **PASS** — `rg -n "@dataclass" packages services scripts` returns no matches; remaining dataclasses are test-only evaluator subclasses (`tests/quality/agents/evaluators.py:58`, `tests/quality/agents/evaluators.py:88`) documented as framework-mandated (`agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/signposts.md:21`).
2. No legacy if/elif phase dispatches: **PASS** — phase dispatches use `match/case` at `packages/rentl-core/src/rentl_core/orchestrator.py:529`, `packages/rentl-core/src/rentl_core/orchestrator.py:1829`, `packages/rentl-agents/src/rentl_agents/wiring.py:1336`, and `services/rentl-cli/src/rentl/main.py:2772`.
3. No behavioral regressions: **FAIL** — Task 2 migrated models still accept unknown kwargs (dataclass constructors previously rejected these), e.g. `ProviderCapabilities: ACCEPTED model_extra=None`, `ProjectContext: ACCEPTED model_extra=None`, `ToolRegistry: ACCEPTED model_extra=None` from `uv run python` constructor probes; related model configs currently omit `extra="forbid"` (`packages/rentl-llm/src/rentl_llm/providers.py:26`, `packages/rentl-agents/src/rentl_agents/tools/registry.py:73`, `packages/rentl-agents/src/rentl_agents/wiring.py:1105`).
4. CI workflow is real and enforced: **PASS** — workflow triggers on PRs to `main` and runs `make all` (`.github/workflows/ci.yml:4`, `.github/workflows/ci.yml:13`, `.github/workflows/ci.yml:30`); GitHub ruleset is active and requires `make all` on `refs/heads/main` (`gh api repos/trevorWieland/rentl/rulesets/13017577` => `"enforcement":"active"`, required status check context `"make all"`).
5. `make all` passes clean: **PASS** — latest full demo run passed all gates including quality tests (`agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/demo.md:43`, `agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/demo.md:47`) and no `SKIP_GATE` override references were found in repository files (`rg -n "SKIP_GATE|skip_gate"`).

## Demo Status
- Latest run: PASS (Run 3, 2026-02-19)
- Demo evidence is convincing for full-gate execution (`agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/demo.md:43`).
- Run 2 failure is documented as LLM non-determinism and was followed by a passing full run (`agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/demo.md:35`, `agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/demo.md:43`).

## Standards Adherence
- `pydantic-only-schemas`: violation (Medium) — Pydantic test schemas use raw annotations without `Field(..., description=...)` (`tests/unit/rentl-agents/test_factory.py:19`, `tests/unit/rentl-agents/test_factory.py:20`, `tests/unit/rentl-agents/test_factory.py:26`, `tests/unit/rentl-agents/test_factory.py:27`).
- `modern-python-314`: PASS — required legacy phase dispatches are converted to `match/case` and dict union is used (`packages/rentl-core/src/rentl_core/orchestrator.py:529`, `packages/rentl-agents/src/rentl_agents/wiring.py:1336`, `services/rentl-cli/src/rentl/main.py:2772`, `packages/rentl-agents/src/rentl_agents/prompts.py:183`).
- `strict-typing-enforcement`: violation (Medium) — same test schema fields violate mandatory `Field(..., description=...)` usage for Pydantic fields (`tests/unit/rentl-agents/test_factory.py:19`, `tests/unit/rentl-agents/test_factory.py:20`, `tests/unit/rentl-agents/test_factory.py:26`, `tests/unit/rentl-agents/test_factory.py:27`).
- `make-all-gate`: PASS — CI runs `make all` on PRs and merge-blocking ruleset requires `make all` status (`.github/workflows/ci.yml:4`, `.github/workflows/ci.yml:13`; ruleset `13017577`).
- `address-deprecations-immediately`: PASS — deprecations are elevated to errors in pytest and Makefile test targets (`pyproject.toml:73`, `Makefile:69`, `Makefile:74`, `Makefile:79`).
- `no-placeholder-artifacts`: PASS — run metadata path no longer uses `placeholder.*` and test stub was replaced by an executable validation test (`packages/rentl-core/src/rentl_core/orchestrator.py:1528`, `tests/unit/benchmark/test_config.py:130`).
- `prefer-dependency-updates`: PASS — dependency specs use compatible ranges with upper major bounds for external deps and install target uses upgrade mode (`pyproject.toml:9`, `pyproject.toml:10`, `Makefile:43`, `services/rentl-api/pyproject.toml:9`, `services/rentl-cli/pyproject.toml:13`).
- `id-formats`: PASS — `HeadToHeadResult.line_id` uses `LineId`, and runtime `run_id` extraction validates UUIDv7 (`packages/rentl-schemas/src/rentl_schemas/benchmark/rubric.py:22`, `packages/rentl-agents/src/rentl_agents/runtime.py:559`).
- `api-response-format`: PASS — health endpoint returns `ApiResponse` envelope with `data`, `error`, and `meta` (`services/rentl-api/src/rentl_api/main.py:19`, `services/rentl-api/src/rentl_api/main.py:25`, `packages/rentl-schemas/src/rentl_schemas/responses.py:53`).

## Regression Check
- Constructor strictness regression pattern has recurred: Task 3 previously failed for unknown-kwarg acceptance and was fixed (`agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/audit-log.md:10`, `agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/audit-log.md:11`), but the same regression remains in Task 2 models (new evidence in this audit).
- Resolved signposts were not reopened without new evidence: Task 3 signpost remains resolved for its files; the current failure is on different Task 2 files (`agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/signposts.md:12`).
- Demo instability risk is still present for quality tests (run 2 fail, run 3 pass), indicating intermittent non-determinism but not a current blocking demo failure (`agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/audit-log.md:22`, `agent-os/specs/2026-02-19-1531-s0146-codebase-modernization-ci-enforcement/audit-log.md:23`).

## Action Items

### Fix Now
- Restore dataclass constructor strictness in Task 2 migrated models by enforcing `extra="forbid"` (or equivalent) so unknown kwargs raise validation errors (`packages/rentl-llm/src/rentl_llm/providers.py:26`, `packages/rentl-agents/src/rentl_agents/tools/game_info.py:13`, `packages/rentl-agents/src/rentl_agents/tools/registry.py:73`, `packages/rentl-agents/src/rentl_agents/factory.py:106`, `packages/rentl-agents/src/rentl_agents/layers.py:58`, `packages/rentl-agents/src/rentl_agents/layers.py:465`, `packages/rentl-agents/src/rentl_agents/templates.py:268`, `packages/rentl-agents/src/rentl_agents/wiring.py:1105`, `packages/rentl-agents/src/rentl_agents/wiring.py:1125`).
- Replace raw test schema fields with `Field(..., description=...)` in `MockInput`/`MockOutput` (`tests/unit/rentl-agents/test_factory.py:19`, `tests/unit/rentl-agents/test_factory.py:20`, `tests/unit/rentl-agents/test_factory.py:26`, `tests/unit/rentl-agents/test_factory.py:27`).

### Deferred
- None.
