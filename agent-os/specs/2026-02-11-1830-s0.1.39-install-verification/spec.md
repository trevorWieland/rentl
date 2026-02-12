spec_id: s0.1.39
issue: https://github.com/trevorWieland/rentl/issues/39
version: v0.1

# Spec: Install Verification (uvx/uv tool)

## Problem

Users cannot install rentl via `uvx rentl` because the package is not published to PyPI. The primary install method for end users should be as simple as running `uvx rentl init` on a fresh machine.

## Goals

- Enable `uvx rentl` as the primary install method for end users
- Verify the full install → init → run workflow works on a clean environment
- Ensure README install instructions are accurate and copy-pasteable

## Non-Goals

- GUI or web-based installation
- Docker-based installation
- pip-based installation (uvx is the primary method)

## Acceptance Criteria

End-user acceptance (via uvx):

- [ ] `uvx rentl --version` outputs the correct version on a fresh machine
- [ ] `uvx rentl init` creates a valid project structure with all expected files
- [ ] `uvx rentl init` prompts for API key configuration
- [ ] `uvx rentl run-pipeline` completes successfully on the initialized project
- [ ] README install instructions are copy-pasteable and verified accurate

Developer verification (before shipping):

- [ ] `make all` passes including lint, typecheck, and all test tiers
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Fresh install must succeed** — `uvx rentl init` works on a machine that has never seen rentl
2. **README install instructions are accurate** — The documented commands must match what actually works
3. **Full verification gate passes** — `make all` must pass after installation and setup
4. **No skipped tests** — All test tiers must pass without skipping
