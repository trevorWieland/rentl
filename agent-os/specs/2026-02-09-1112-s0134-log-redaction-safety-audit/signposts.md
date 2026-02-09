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

- **Task:** Demo Step 5
- **Status:** unresolved
- **Problem:** Demo plan specifies a test secret value `sk-hardcoded-secret` that contains hyphens, which don't match the `sk-[a-zA-Z0-9]{20,}` pattern in DEFAULT_PATTERNS.
- **Evidence:** Running `rentl check-secrets` on a config with `api_key_env = "sk-hardcoded-secret"` returns exit code 0 (clean). When tested with a pattern-compliant value `sk-test12345678901234567890abcdefgh` (alphanumeric only), the scanner correctly detects it and returns exit code 1 with security findings.
- **Evidence:** Demo execution Step 5 FAIL — scanner did not detect the hardcoded secret in the test config file.
- **Impact:** The demo step as written will always fail unless the test value is changed to match the pattern (alphanumeric only after `sk-`).
- **Root cause:** Demo plan author used a secret value with hyphens; the redaction pattern only matches alphanumeric characters after the `sk-` prefix.
- **Solution:** Update demo.md Step 5 to use a pattern-compliant test secret value like `sk-hardcodedsecret1234567890abc` or expand the pattern to include hyphens if that's a valid secret format.
- **Files affected:** `agent-os/specs/2026-02-09-1112-s0134-log-redaction-safety-audit/demo.md`
