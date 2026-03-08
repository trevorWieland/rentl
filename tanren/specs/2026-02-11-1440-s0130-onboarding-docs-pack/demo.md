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

### Run 1 — Full onboarding verification (2026-02-11 18:45)
- Step 1 [RUN]: PASS — All 13 commands match between CLI and README with identical descriptions
- Step 2 [RUN]: PASS — All commands have meaningful help text, no Raises: sections, all options documented
- Step 3 [RUN]: PASS — README quickstart contains all four steps (init, doctor, run-pipeline, export) with copy-pasteable examples and explanations
- Step 4 [RUN]: PASS — All config sections and keys from rentl.toml.example are documented in README Configuration section
- Step 5 [RUN]: PASS — All 6 environment variables from .env.example are documented in README Environment Variables section
- Step 6 [RUN]: PASS — docs/troubleshooting.md exists and covers all 4 required failure modes (Missing API Key, Invalid Config, Connection Failure, Schema Mismatch) with symptom/cause/fix patterns and rentl doctor reference
- Step 7 [RUN]: PASS — make check passed (format, lint, type, 837 unit tests)
- **Overall: PASS**
