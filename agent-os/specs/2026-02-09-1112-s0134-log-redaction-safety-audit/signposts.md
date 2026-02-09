# Signposts

- **Task:** Task 5 (`check-secrets`)
- **Status:** unresolved
- **Problem:** In git repositories, `.env` files that exist but are not ignored can pass silently unless they are already tracked.
- **Evidence:** Control flow in `services/rentl-cli/src/rentl_cli/main.py:2692` only checks tracked status via `git ls-files`; `.gitignore` fallback is gated behind `if not is_git_repo` at `services/rentl-cli/src/rentl_cli/main.py:2712`, so it never runs inside a valid git repo.
- **Evidence:** Repro command output from a fresh git repo with `rentl.toml` + `.env` (untracked, no `.gitignore`): `exit_code= 0` and `PASS: No hardcoded secrets detected`.
- **Impact:** This violates the Task 5 contract to warn on `.env` presence when not in `.gitignore`, allowing a risky `.env` state to go undetected until after a commit.
