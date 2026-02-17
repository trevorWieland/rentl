status: fail
fix_now_count: 2

# Audit: s0.1.40 Model Default Updates

- Spec: s0.1.40
- Issue: https://github.com/trevorWieland/rentl/issues/124
- Date: 2026-02-17
- Round: 1

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 4/5
- Completion: 3/5
- Security: 5/5
- Stability: 5/5

## Non-Negotiable Compliance
1. **No EOL models in presets**: **PASS** — Presets use `qwen/qwen3-30b-a3b` and `gpt-5-nano` (`packages/rentl-core/src/rentl_core/init.py:33`, `packages/rentl-core/src/rentl_core/init.py:42`). `gpt-5-nano` is present in current OpenAI model docs and not listed on OpenAI deprecations (checked 2026-02-17: https://platform.openai.com/docs/models, https://platform.openai.com/docs/deprecations).
2. **Open-weight default on OpenRouter**: **PASS** — OpenRouter preset defaults to `qwen/qwen3-30b-a3b` (`packages/rentl-core/src/rentl_core/init.py:37`); OpenRouter model page links public model weights (https://openrouter.ai/qwen/qwen3-30b-a3b).
3. **Local preset has no default model**: **PASS** — Local preset has `default_model=None` (`packages/rentl-core/src/rentl_core/init.py:45`, `packages/rentl-core/src/rentl_core/init.py:47`) and CLI prompts `Model ID` when default is absent (`services/rentl-cli/src/rentl/main.py:610`, `services/rentl-cli/src/rentl/main.py:613`).
4. **No silent model fallbacks**: **PASS** — `model_id` is required in both runtime configs (`packages/rentl-agents/src/rentl_agents/runtime.py:57`, `packages/rentl-agents/src/rentl_agents/harness.py:49`), with validation behavior covered in tests (`tests/unit/rentl-agents/test_wiring.py:369`, `tests/unit/rentl-agents/test_harness.py:544`) and reproduced in audit run (`PROFILE_ERROR ('model_id',) Field required`, `HARNESS_ERROR ('model_id',) Field required`).
5. **All model string references updated**: **FAIL** — Stale model strings remain in docs at `agent-os/product/roadmap.md:68` (`gpt-4-turbo`, `gpt-4o-mini`, `llama3.2`), confirmed by repository scan: `rg -n "gpt-4-turbo|gpt-4o-mini|llama3\\.2" .`.

## Demo Status
- Latest run: PASS (Run 1, 2026-02-17) (`agent-os/specs/2026-02-17-1200-s0.1.40-model-default-updates/demo.md:25`)
- All five demo steps are marked PASS, including preset behavior, required `model_id` validation, and stale-string scan scope (`agent-os/specs/2026-02-17-1200-s0.1.40-model-default-updates/demo.md:26`, `agent-os/specs/2026-02-17-1200-s0.1.40-model-default-updates/demo.md:31`).

## Standards Adherence
- `ux/frictionless-by-default`: PASS — Interactive preset flow with guided defaults and Local model prompt is implemented (`services/rentl-cli/src/rentl/main.py:588`, `services/rentl-cli/src/rentl/main.py:613`).
- `ux/copy-pasteable-examples`: PASS — Updated docs use concrete runnable examples and current model names (`README.md:193`, `packages/rentl-agents/README.md:115`, `scripts/validate_agents.py:18`).
- `ux/stale-reference-prevention`: **Violation (High)** — Standard requires verifying references against actual code/config truth (`agent-os/standards/ux/stale-reference-prevention.md:3`), but stale model references persist in roadmap (`agent-os/product/roadmap.md:68`).
- `testing/make-all-gate`: PASS — `make all` executed in this audit and passed (format, lint, type, unit/integration/quality tests).
- `testing/mandatory-coverage`: PASS — Full test gate passed and behavior-focused tests cover key acceptance paths (`tests/unit/cli/test_main.py:2008`, `tests/unit/rentl-agents/test_wiring.py:369`, `tests/unit/rentl-agents/test_harness.py:544`).
- `python/strict-typing-enforcement`: **Violation (Medium)** — Standard requires Pydantic fields to use `Field(..., description=...)` (`agent-os/standards/python/strict-typing-enforcement.md:32`), but runtime schema fields are raw annotations in touched configs (`packages/rentl-agents/src/rentl_agents/runtime.py:55`, `packages/rentl-agents/src/rentl_agents/harness.py:47`).
- `global/no-placeholder-artifacts`: PASS — No placeholder/test-skip artifacts were found in scoped implementation; full verification passed.
- `global/address-deprecations-immediately`: PASS — Full gate passed with no deprecation-blocking failures.

## Signpost Cross-Reference
- `signposts.md` is not present in this spec folder; no documented signpost constraints or deferrals to cross-reference for round 1.

## Regression Check
- `audit-log.md` shows all prior task audits and demo run as PASS (`agent-os/specs/2026-02-17-1200-s0.1.40-model-default-updates/audit-log.md:8`).
- No previously fixed item regressed in runtime behavior/tests; the current failures are audit-scope compliance gaps (stale roadmap reference, strict typing schema-field rule) rather than test regressions.

## Action Items

### Fix Now
- Remove stale model strings from roadmap spec listing (`agent-os/product/roadmap.md:68`) to satisfy non-negotiable #5 and `ux/stale-reference-prevention` (audit round 1).
- Add `Field(..., description="...")` schema declarations for `ProfileAgentConfig` and `AgentHarnessConfig` fields (`packages/rentl-agents/src/rentl_agents/runtime.py:55`, `packages/rentl-agents/src/rentl_agents/harness.py:47`) to satisfy `python/strict-typing-enforcement` (audit round 1).

### Deferred
- None.
