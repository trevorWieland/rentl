# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): FAIL — Task marked complete without the required unit-test update in `tests/unit/core/test_doctor.py` for dotenv loading behavior.
- **Task 2** (round 2): FAIL — Task still marked complete without dotenv-loading doctor-context unit coverage in `tests/unit/core/test_doctor.py`; coverage was added in `tests/unit/cli/test_main.py` instead.
- **Task 2** (round 3): FAIL — New core doctor dotenv tests contain incorrect `.env.local` precedence guidance and do not assert actual `.env`/`.env.local` load behavior.
- **Task 1** (round 1): PASS — Spec scaffold commit `e2dad4e` added all required docs (`spec.md`, `plan.md`, `demo.md`, `standards.md`, `references.md`) with no task-scope violations.
- **Task 3** (round 1): FAIL — `rentl init` accepts out-of-range numeric provider menu input as Custom, and CLI provider-selection branches lack direct test coverage.
- **Task 3** (round 2): PASS — Provider menu now rejects out-of-range input with validation error, and provider selection/custom URL loop behavior is covered by unit tests.
- **Task 4** (round 1): FAIL — Export-completed summary branch labels `Output files:` but only prints `output_dir` instead of concrete exported file paths, and tests do not cover actual file-path rendering.
- **Task 4** (round 2): FAIL — Export-complete summary derives file list from configured target languages instead of actual exported outputs, so it can display nonexistent files under `run-pipeline --target-language` overrides.
- **Task 3** (round 3): PASS — Re-audit verified provider preset menu behavior remains correct, signpost 3 resolution is implemented, and focused Task 3 unit/integration tests pass.
- **Task 5** (round 1): FAIL — `README.md` does not include the required license link; the License section only states that no license file exists.
- **Task 5** (round 2): FAIL — `README.md` now has a license URL, but it points to `https://github.com/trevorWieland/rentl/blob/main/LICENSE` which returns HTTP 404, so Task 5's license-link accuracy requirement is still unmet.
- **Task 5** (round 3): FAIL — `README.md` License section now has no hyperlink at all, so Task 5's "Links to license" requirement in `plan.md` remains unmet.
- **Task 5** (round 4): PASS — Verified signpost 6 resolution is implemented: `README.md` now links to a real root `LICENSE` file, and Task 5 requirements remain satisfied.
- **Task 6** (round 1): FAIL — New onboarding E2E test calls `init --target-dir`, but `init` has no `--target-dir` option, so the test fails immediately with exit code 2.
- **Task 6** (round 2): FAIL — Onboarding E2E export step calls unsupported `rentl export` flags (`--run-id`, `--target-language`) and omits required export args, so the scenario still fails before export execution.
- **Task 5** (round 5): FAIL — `README.md` contains inaccurate command guidance: Quick Start uses invalid bare `rentl export`, and Development lists nonexistent Make targets (`test-int`, `test-all`).
- **Task 5** (round 6): PASS — README Quick Start export example now includes required flags, and Development Make targets match the current Makefile.
- **Demo** (run 1): FAIL — OpenRouter preset uses non-existent model ID "openai/gpt-4.1", blocking connectivity check and full onboarding flow (1 run, 0 verified)
- **Task 7** (round 1): PASS — OpenRouter preset now uses `openai/gpt-4-turbo`, related init defaults/tests were updated, and the model ID was verified in OpenRouter's live models list.
