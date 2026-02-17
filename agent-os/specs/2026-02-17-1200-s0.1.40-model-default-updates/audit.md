status: fail
fix_now_count: 3

# Audit: s0.1.40 Model Default Updates

- Spec: s0.1.40
- Issue: https://github.com/trevorWieland/rentl/issues/124
- Date: 2026-02-17
- Round: 2

## Rubric Scores (1-5)
- Performance: 5/5
- Intent: 4/5
- Completion: 3/5
- Security: 5/5
- Stability: 5/5

## Non-Negotiable Compliance
1. **No EOL models in presets**: **PASS** — Presets now use `qwen/qwen3-30b-a3b` and `gpt-5-nano` (`packages/rentl-core/src/rentl_core/init.py:37`, `packages/rentl-core/src/rentl_core/init.py:42`). `gpt-5-nano` is listed in OpenAI’s current models docs and not listed on OpenAI’s deprecations page (checked 2026-02-17: https://platform.openai.com/docs/models, https://platform.openai.com/docs/deprecations).
2. **Open-weight default on OpenRouter**: **PASS** — OpenRouter preset defaults to `qwen/qwen3-30b-a3b` (`packages/rentl-core/src/rentl_core/init.py:35`, `packages/rentl-core/src/rentl_core/init.py:37`), and OpenRouter’s model page links public model weights for this model (https://openrouter.ai/qwen/qwen3-30b-a3b).
3. **Local preset has no default model**: **PASS** — Local preset has `default_model=None` (`packages/rentl-core/src/rentl_core/init.py:45`, `packages/rentl-core/src/rentl_core/init.py:47`), and CLI prompts `Model ID` when no preset default exists (`services/rentl-cli/src/rentl/main.py:610`, `services/rentl-cli/src/rentl/main.py:613`).
4. **No silent model fallbacks**: **PASS** — `model_id` is required in both runtime schemas (`packages/rentl-agents/src/rentl_agents/runtime.py:58`, `packages/rentl-agents/src/rentl_agents/harness.py:49`) and validated by tests (`tests/unit/rentl-agents/test_wiring.py:369`, `tests/unit/rentl-agents/test_harness.py:544`).
5. **All model string references updated**: **PASS** — Repository scan for stale strings (`gpt-4-turbo`, `gpt-4o-mini`, `llama3.2`) outside historical spec docs returned no matches: `rg -n "gpt-4-turbo|gpt-4o-mini|llama3\\.2" -S --glob '!agent-os/specs/**' --glob '!.venv/**'`.

## Demo Status
- Latest run: PASS (Run 2, 2026-02-17) (`agent-os/specs/2026-02-17-1200-s0.1.40-model-default-updates/demo.md:33`)
- All 5 demo steps are marked PASS with explicit evidence for presets, Local model prompt behavior, required `model_id` validation, and stale-string scan scope (`agent-os/specs/2026-02-17-1200-s0.1.40-model-default-updates/demo.md:34`, `agent-os/specs/2026-02-17-1200-s0.1.40-model-default-updates/demo.md:39`).

## Standards Adherence
- `ux/frictionless-by-default`: PASS — Guided init flow and safe preset defaults are implemented, with explicit prompt when no preset model default exists (`services/rentl-cli/src/rentl/main.py:588`, `services/rentl-cli/src/rentl/main.py:613`).
- `ux/copy-pasteable-examples`: PASS — Updated docs/config examples include concrete runnable model values in key spec-touched docs (`README.md:193`, `packages/rentl-agents/README.md:148`, `scripts/validate_agents.py:18`).
- `ux/stale-reference-prevention`: **Violation (Medium)** — Docs and test assertion text still carry stale preset/model wording not aligned with current implementation (`README.md:53`, `README.md:311`, `README.md:314`, `tests/quality/cli/test_preset_validation.py:152`) against rule requirement to verify against actual current config/CLI truth (`agent-os/standards/ux/stale-reference-prevention.md:3`).
- `testing/make-all-gate`: PASS — Full gate run in this audit round succeeded (`make all`: format/lint/type + unit 841 + integration 91 + quality 9, all passed).
- `testing/mandatory-coverage`: PASS — The full verification gate executed and passed, and behavior-oriented tests cover required init/runtime behavior (`tests/unit/cli/test_main.py:2008`, `tests/unit/rentl-agents/test_wiring.py:369`, `tests/unit/rentl-agents/test_harness.py:544`).
- `python/strict-typing-enforcement`: **Violation (Medium)** — Pydantic schema fields remain as raw annotations without `Field(..., description=...)` in spec-touched runtime configs (`packages/rentl-agents/src/rentl_agents/runtime.py:56`, `packages/rentl-agents/src/rentl_agents/harness.py:47`) against `Field` requirement (`agent-os/standards/python/strict-typing-enforcement.md:32`).
- `global/no-placeholder-artifacts`: PASS — No placeholder hashes/skipped-test artifacts were identified in scoped implementation, and gate executed green.
- `global/address-deprecations-immediately`: PASS — Gate completed cleanly with no deprecation-driven failures requiring immediate remediation.

## Signpost Cross-Reference
- `signposts.md` is not present in this spec folder, so there are no signpost constraints/deferrals to apply in this round.
- `plan.md` had no open unchecked fix items before this audit; the new Fix Now items introduced in this round are non-duplicates.

## Regression Check
- Prior round fixes did not regress: stale strings removed from roadmap remain removed, and required `model_id` behavior remains enforced (`agent-os/specs/2026-02-17-1200-s0.1.40-model-default-updates/audit-log.md:15`).
- The current round failures are documentation/test-string consistency and strict-typing standards conformance gaps, not runtime behavior regressions.

## Action Items

### Fix Now
- Update README references to align with current model defaults and model-agnostic Local preset wording (`README.md:53`, `README.md:311`, `README.md:314`).
- Update stale test assertion text that still references `Local/Ollama` instead of `Local` (`tests/quality/cli/test_preset_validation.py:152`).
- Add `Field(..., description=...)` annotations for remaining schema fields in `ProfileAgentConfig` and `AgentHarnessConfig` that are still raw annotations (`packages/rentl-agents/src/rentl_agents/runtime.py:56`, `packages/rentl-agents/src/rentl_agents/harness.py:47`).

### Deferred
- None.
