# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): FAIL — Package/module rename implementation is present, but Task 2's required `make all` verification gate currently fails in quality (`tests/quality/agents/test_edit_agent.py:183`).
- **Task 2** (round 2): FAIL — Task was re-checked without the required `uv sync` command evidence; `signposts.md` documents only `make all` output (`signposts.md:74`).
- **Task 1** (round 1): PASS — Task commit `d69c907` correctly created the spec documentation set (`spec.md`, `plan.md`, `standards.md`, `demo.md`, `references.md`) with no task-level standards or non-negotiable violations.
- **Task 3** (round 1): PASS — `uv build --package rentl --no-sources` succeeded and produced valid `dist/rentl-0.1.0.tar.gz` and `dist/rentl-0.1.0-py3-none-any.whl` artifacts.
- **Task 4** (round 1): PASS — All five packages are published at `0.1.0` and an isolated `uv pip install rentl==0.1.0` resolves `rentl-core`, `rentl-io`, `rentl-llm`, and `rentl-schemas`.
- **Task 5** (round 1): PASS — Commit `3dcaf43` resolves missing `rentl-agents` runtime dependency and version sync drift; `uvx rentl version` now returns `rentl v0.1.4`.
- **Task 6** (round 1): FAIL — Commit `3c79c23` only flips the Task 6 checkbox in `plan.md` and does not persist required `uvx rentl init` verification evidence.
- **Task 5** (round 2): FAIL — Spec requires `uvx rentl --version` (`spec.md:27`), but CLI exits 2 with `No such option: --version`; Task 5 unchecked with fix items.
- **Task 5** (round 3): PASS — Commit `8742d01` correctly implements root `--version`, adds unit coverage, and includes clean-environment verification evidence with exit code 0.
- **Task 6** (round 2): PASS — Task 6 requirements are satisfied with persisted clean-directory `uvx rentl init` evidence and config validation evidence in `signposts.md`.
- **Task 7** (round 1): FAIL — Packaging fix is implemented, but Task 7 evidence shows `run-pipeline` runtime failure (`signposts.md:495`) after setting an invalid API key (`signposts.md:490`), so successful end-to-end completion is unverified.
- **Task 7** (round 2): PASS — Commit `bd8f87a` resolves the prior Task 7 audit item by adding valid-credentials `uvx --from rentl==0.1.7 rentl run-pipeline` completion evidence with `error: null`, all phases `completed`, and exit code 0 in `signposts.md`.
- **Task 8** (round 1): FAIL — `README.md:63-72` is presented as runnable `bash`, but those lines only set shell variables and do not update `.env`; this violates `copy-pasteable-examples` (`standards.md:8-9`) and Task 8's verbatim-command requirement.
- **Task 8** (round 2): FAIL — `README.md:63-72` still presents shell assignments in a runnable `bash` block while Step 2 requires writing `.env`; executing that block leaves `.env` unchanged, so `copy-pasteable-examples` (`standards.md:8-9`) remains unmet.
- **Task 8** (round 3): PASS — Commit `639df7f` resolves the remaining Task 8 fix item by changing Step 2 to an `.env` content block (`README.md:63`) and preserving a runnable mutation command (`README.md:77`), satisfying `copy-pasteable-examples` (`standards.md:8-9`).
- **Task 9** (round 1): FAIL — Commit `b8f6b50` only checks off `Task 9` in `plan.md` without persisting `make all` verification evidence, so required developer gate completion is unverified (`plan.md:66-68`, `spec.md:35`, `standards.md:11-12`).
- **Task 9** (round 2): PASS — Commit `67f9af5` adds persisted `make all` evidence in `signposts.md:764` with explicit `Exit code: 0` and passing format/lint/type/unit/integration/quality tiers, satisfying `spec.md:35` and `standards.md:11-12`.
- **Task 10** (round 1): FAIL — `scripts/publish.sh --dry-run` returns 0 but does not execute `uv publish --dry-run` because of a broken condition at `scripts/publish.sh:105`, so dry-run publish validation is not actually performed.
- **Task 10** (round 2): FAIL — Commit `cdb6860` fixes `uv publish --dry-run` invocation but introduces an unconditional `source .env` at `scripts/publish.sh:106`; dry-run now exits 1 with `.env: No such file or directory` when `.env` is absent.
- **Demo** (run 1): PASS — All 5 steps executed successfully: version check, init, API config, pipeline run (all phases completed), README verification (5 run, 0 verified)
- **Spec Audit** (round 1): FAIL — Performance 5/5, Intent 5/5, Completion 4/5, Security 5/5, Stability 4/5 (fix-now: 1)
- **Task 11** (round 1): FAIL — Init refactor regressed generated endpoint fields: `api_key_env` no longer matches `.env.example` and `provider_name` is serialized as a `ProviderCapabilities(...)` repr instead of a provider name string.
- **Task 11** (round 2): PASS — Commit `aa5f663` fixes env-var standardization (`RENTL_LOCAL_API_KEY`) and provider-name serialization (`detect_provider(...).name`) with unit/integration regression coverage passing.
- **Task 12** (round 1): FAIL — `tests/quality/cli/test_preset_validation.py:97-98` still rewrites `.env`, so Task 12's required removal of `.env` workaround and init-output validation (`plan.md:96-97`, `no-mocks-for-quality-tests`) is not satisfied.
- **Task 12** (round 2): FAIL — Commit `3f5a572` reduces `.env` rewriting but still mutates `.env` via `env_path.write_text(updated_env)` (`tests/quality/cli/test_preset_validation.py:96-106`), so Task 12's explicit “remove `.env` file writing workarounds” requirement (`plan.md:96`) remains unmet.
- **Task 12** (round 3): PASS — Commit `1464b30` removes remaining `.env` mutation in `tests/quality/cli/test_preset_validation.py` and verifies doctor via injected standardized env var, satisfying Task 12 cleanup requirements with no quality-test skips detected.
- **Demo** (run 2): FAIL — Task 11 env var standardization changes exist in local codebase but not in published PyPI v0.1.7; `uvx rentl==0.1.7 init` generates `OPENROUTER_API_KEY` instead of standardized `RENTL_LOCAL_API_KEY` (4 run, 0 verified, 1 failed)
- **Task 13** (round 1): PASS — Commit `d6d8057` applies lock-step `0.1.8` version updates across all publishable packages and records Task 11 env-var verification evidence for `uvx --from rentl==0.1.8 rentl init` in `signposts.md`.
- **Demo** (run 4): PASS — All 5 [RUN] steps executed successfully: version check (v0.1.8), init (standardized RENTL_LOCAL_API_KEY), API config, pipeline run (all 7 phases completed with 2 lines translated), README verification (5 run, 0 verified)
- **Spec Audit** (round 2): PASS — Performance 5/5, Intent 5/5, Completion 5/5, Security 5/5, Stability 5/5 (fix-now: 0)
- **Walk-spec gate** (2026-02-12): FAIL — `make all` failed: `test_translate_phase_produces_translated_output` timed out at 30s (`tests/quality/pipeline/test_golden_script_pipeline.py`). 11 passed, 1 failed in quality tier. Task 9 unchecked; fix item added to plan.
- **Task 14** (round 1): PASS — Commit `ae8dc5c` satisfies Task 14 by adding Demo Run 3 PASS evidence for `uvx --from rentl==0.1.8`, standardized `RENTL_LOCAL_API_KEY` init output, and updated README API-key instructions.
- **Demo** (run 5): PASS — All 5 [RUN] steps executed successfully: version check (v0.1.8), init (standardized RENTL_LOCAL_API_KEY), API config, pipeline run (all 7 phases completed with 2 lines translated), README verification (5 run, 0 verified)
- **Spec Audit** (round 3): FAIL — Performance 4/5, Intent 5/5, Completion 4/5, Security 5/5, Stability 3/5 (fix-now: 1)
- **Task 14** (round 2): PASS — Commit `ae8dc5c` fully satisfies Task 14 scope: `plan.md` task check-off, `demo.md` Run 3 records all five steps as PASS on `rentl==0.1.8`, and README Step 2 API-key instructions were updated to standardized `RENTL_LOCAL_API_KEY`.
- **Demo** (run 6): PASS — All 5 [RUN] steps executed successfully: version check (v0.1.8), init (standardized RENTL_LOCAL_API_KEY), API config, pipeline run (all 7 phases completed with 2 lines translated), README verification (5 run, 0 verified)
- **Spec Audit** (round 4): FAIL — Performance 4/5, Intent 5/5, Completion 4/5, Security 5/5, Stability 2/5 (fix-now: 1)
- **Task 14** (round 3): PASS — Commit `ae8dc5c` remains clean: Run 3 evidence in `demo.md` covers all five demo steps on `rentl==0.1.8`, verifies standardized `RENTL_LOCAL_API_KEY`, and keeps README commands aligned with the documented flow.
- **Demo** (run 7): PASS — All 5 [RUN] steps executed successfully: version check (v0.1.8), init (standardized RENTL_LOCAL_API_KEY), API config, pipeline run (all 7 phases completed with 2 lines translated), README verification (5 run, 0 verified)
- **Spec Audit** (round 5): FAIL — Performance 4/5, Intent 5/5, Completion 4/5, Security 5/5, Stability 2/5 (fix-now: 1; intermittent `test_translate_phase_produces_translated_output` failure with `Hit request limit (4)` on repeated runs)
- **Task 14** (round 4): PASS — Commit `ae8dc5c` still satisfies Task 14: `plan.md` check-off is present, `demo.md` Run 3 records all five steps passing on `rentl==0.1.8`, and README Step 2 uses standardized `RENTL_LOCAL_API_KEY`.
- **Demo** (run 8): PASS — All 5 [RUN] steps executed successfully: version check (v0.1.8), init (standardized RENTL_LOCAL_API_KEY), API config, pipeline run (all 7 phases completed with 3 lines translated), README verification (5 run, 0 verified)
