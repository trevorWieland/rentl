# Standards: Documentation Placeholders, CLI Surface & UX Polish

## Primary Standards (directly violated)

1. **ux/copy-pasteable-examples** — All command examples in docs must be executable without modification (59 violations)
2. **ux/stale-reference-prevention** — Cross-reference audits must verify against actual CLI output and config files (3 violations)
3. **ux/frictionless-by-default** — Guided setup and safe defaults for effortless first runs (5 violations)
4. **architecture/thin-adapter-pattern** — Surface layers are thin adapters; all business logic lives in Core Domain (3 violations)
5. **python/cli-help-docstring-gating** — Use form-feed to hide internal docstring sections from Typer help output (4 violations)
6. **ux/trust-through-transparency** — No silent stalls; every phase, error, and status must be visible and explainable (3 violations)
7. **ux/progress-is-product** — Status, phase completion, and QA visibility must be immediate and unambiguous (3 violations)

## Supporting Standards (touched by changes)

8. **testing/mandatory-coverage** — Coverage mandatory for all features; extracted core logic needs tests
9. **testing/make-all-gate** — Gate tiers: make check (task), make ci (CI PR), make all (spec)
