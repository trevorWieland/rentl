# Standards: Model Default Updates

## Applicable Standards

1. **ux/frictionless-by-default** — Guided setup and safe defaults for effortless first runs. Directly relevant: preset updates define what new users see on `rentl init`.

2. **ux/copy-pasteable-examples** — All command examples in docs must be executable without modification. Relevant: docs and README examples referencing model names must use current models.

3. **ux/stale-reference-prevention** — Cross-reference audits must verify against actual CLI output and config files. Relevant: all model references in docs must match actual code.

4. **testing/make-all-gate** — Require `make all` to pass before finalizing work.

5. **testing/mandatory-coverage** — Coverage mandatory for all features; tests must exercise actual behavior.

6. **python/strict-typing-enforcement** — Never use `Any` or `object` in types; all Pydantic fields use `Field` with description. Relevant: `EndpointPreset.default_model` type change to `str | None`.

7. **global/no-placeholder-artifacts** — Never commit placeholder values; all artifacts must be functional and verified.

8. **global/address-deprecations-immediately** — Deprecation warnings must be addressed immediately. Directly relevant: removing EOL model references.
