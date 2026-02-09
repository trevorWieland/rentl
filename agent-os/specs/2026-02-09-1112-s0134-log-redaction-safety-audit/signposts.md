# Signposts

- **Task:** Task 5 (`check-secrets`)
- **Status:** resolved
- **Problem:** In git repositories, `.env` files that exist but are not ignored can pass silently unless they are already tracked.
- **Evidence:** Control flow in `services/rentl-cli/src/rentl_cli/main.py:2692` only checks tracked status via `git ls-files`; `.gitignore` fallback is gated behind `if not is_git_repo` at `services/rentl-cli/src/rentl_cli/main.py:2712`, so it never runs inside a valid git repo.
- **Evidence:** Repro command output from a fresh git repo with `rentl.toml` + `.env` (untracked, no `.gitignore`): `exit_code= 0` and `PASS: No hardcoded secrets detected`.
- **Impact:** This violates the Task 5 contract to warn on `.env` presence when not in `.gitignore`, allowing a risky `.env` state to go undetected until after a commit.
- **Solution:** Added `.gitignore` check in the `else` branch after checking tracked status (when file is untracked); now both tracked and untracked `.env` files are evaluated against `.gitignore` rules.
- **Resolution:** do-task round 3 (2026-02-09)
- **Files affected:** `services/rentl-cli/src/rentl_cli/main.py:2692-2726`, `tests/unit/cli/test_check_secrets.py:183-235`

- **Task:** Task 6 (redactor bootstrap + CLI wiring)
- **Status:** resolved
- **Problem:** The new command-log redaction test can pass without validating any persisted logs, so Task 6 acceptance ("debug log confirms redaction happened") is not currently verified.
- **Evidence:** `test_redaction_in_command_logs` guards assertions with `if log_files` and invokes `doctor`, which does not emit command logs (`tests/unit/cli/test_main.py:2036-2059`, `services/rentl-cli/src/rentl_cli/main.py:308-394`).
- **Evidence:** Repro output from running the same flow: `exit_code 10`, `log_file_count 0`.
- **Impact:** Regressions in CLI redaction/debug visibility can slip through CI while the test remains green.
- **Solution:** Replaced the test with a direct integration test that creates a log entry with a secret via the storage layer, verifies redaction occurs, and confirms the `redaction_applied` debug event is emitted.
- **Resolution:** do-task round 4 (2026-02-09)
- **Files affected:** `tests/unit/cli/test_main.py:2036-2095`
