# Demo: Documentation Placeholders, CLI Surface & UX Polish

This spec brings documentation, CLI hygiene, and observability up to standard. Docs should be real and copy-pasteable, CLI commands should be thin wrappers over core logic, and users should get visibility into what's happening — even when running headlessly. In this demo, we'll prove all three by checking docs for placeholders, verifying CLI architecture, and confirming observability works.

## Environment

- API keys: `RENTL_OPENROUTER_API_KEY`, `RENTL_LOCAL_API_KEY`, `RENTL_QUALITY_API_KEY` via `.env`
- External services:
  - OpenRouter API at https://openrouter.ai/api/v1 — verified (200)
- Setup: none

## Steps

1. **[RUN]** Grep user-facing docs for `<placeholder>` angle-bracket patterns — expected: zero matches in README.md, CONTRIBUTING.md, docs/troubleshooting.md, WORKFLOW-GUIDE.md
2. **[RUN]** Verify README env var names match canonical names (`RENTL_LOCAL_API_KEY`, `RENTL_QUALITY_API_KEY`) — expected: no references to old `OPENROUTER_API_KEY`/`OPENAI_API_KEY` as env var names
3. **[RUN]** Run `rentl help` and verify `check-secrets`, `migrate`, and `benchmark` appear in output — expected: all three listed
4. **[RUN]** Run `rentl --help` and verify `\f`-gated internal docstring sections are hidden from help output — expected: no internal implementation details visible in help text
5. **[RUN]** Verify extracted core modules exist and have zero imports from CLI surface — expected: `grep -r 'from rentl\.' packages/rentl-core/src/` returns nothing (excluding test fixtures)
6. **[RUN]** Run `rentl init` in a temp directory and verify auto-detection and config preview — expected: detects settings, shows preview, validates config before writing
7. **[RUN]** Run `make all` — expected: all gates pass

## Results

(Appended by run-demo — do not write this section during shaping)
