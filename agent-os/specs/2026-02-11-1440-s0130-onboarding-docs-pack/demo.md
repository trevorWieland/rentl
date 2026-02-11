# Demo: Onboarding Docs Pack

The rentl onboarding experience should guide any user from discovery to first pipeline run. This demo proves that the docs, CLI help, and configuration examples are complete, consistent, and self-sufficient — so both fan translators and professional localization teams can start using rentl without friction.

## Environment

- API keys: Not needed (docs and help text verification only)
- External services: None
- Setup: None

## Steps

1. **[RUN]** Run `rentl --help` and verify every listed command appears in README.md's command table, and vice versa — expected: zero orphaned commands in either direction

2. **[RUN]** Run `rentl <command> --help` for every command and verify each has a meaningful description and all options have help text — expected: no empty, placeholder, or internal-only descriptions (no `Raises:` sections visible)

3. **[RUN]** Verify the README quickstart path is complete: check that `rentl init`, `rentl doctor`, `rentl run-pipeline`, and `rentl export` are all documented with copy-pasteable examples — expected: each step present with command + explanation

4. **[RUN]** Cross-reference `rentl.toml.example` config keys against README configuration section — expected: all config sections documented, no undocumented keys

5. **[RUN]** Cross-reference `.env.example` variables against README environment docs — expected: all env vars documented

6. **[RUN]** Verify `docs/troubleshooting.md` exists and covers: missing API key, invalid config, connection failure, schema migration — expected: each failure mode has a symptom, cause, and fix

7. **[RUN]** Run `make check` to verify no code changes broke anything — expected: all checks pass

## Results

(Appended by run-demo — do not write this section during shaping)
