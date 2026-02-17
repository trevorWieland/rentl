# Standards: Install Verification

## Applied Standards

1. **frictionless-by-default** — Guided setup and safe defaults for effortless first runs
   - The `rentl init` command should guide users through setup with sensible defaults

2. **copy-pasteable-examples** — All command examples in docs must be executable without modification
   - README install instructions must work exactly as written

3. **make-all-gate** — Require `make all` to pass before finalizing work
   - All lint, typecheck, and tests must pass before shipping

4. **mandatory-coverage** — Coverage mandatory for all features
   - New code must have test coverage

5. **three-tier-test-structure** — Tests in unit/integration/quality folders with timing rules
   - Unit <250ms, integration <5s, quality <30s
