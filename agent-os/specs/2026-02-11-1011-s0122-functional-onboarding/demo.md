# Demo: Functional Onboarding

Functional onboarding is the glue that makes rentl's first-run experience seamless. A new user should be able to go from zero to a translated output in a single uninterrupted flow: `rentl init -> rentl doctor -> rentl run-pipeline -> rentl export`. No manual file edits, no cryptic errors, no guessing what to do next.

This matters because it's the first impression. If the onboarding is broken, users never see the pipeline's value. Every gap — a missing `.env` load, an unclear error, a "what now?" after the pipeline finishes — is a point where the user gives up.

## Environment

- API keys: `RENTL_OPENROUTER_API_KEY` available via `.env`
- External services: OpenRouter API reachable
- Setup: none

## Steps

1. **[RUN]** Create an empty temporary directory and run `rentl init` with defaults — expected: project scaffolded with `rentl.toml`, `.env`, seed data file, and `input/`/`out/`/`logs/` directories. Verify provider presets are offered during init (OpenRouter, OpenAI, Local/Ollama).

2. **[RUN]** Set `RENTL_OPENROUTER_API_KEY` in the generated `.env` file and run `rentl doctor` — expected: all 6 diagnostic checks pass (Python version, config file, config valid, workspace dirs, API keys, LLM connectivity). This proves doctor correctly loads `.env` before running checks.

3. **[RUN]** Run `rentl run-pipeline` on the seed data — expected: pipeline completes successfully across all phases (ingest -> context -> pretranslation -> translate -> qa -> edit -> export). Post-run summary includes next steps pointing to `rentl export` and the output directory.

4. **[RUN]** Run `rentl export` — expected: translated output files appear in the configured output directory (`out/`).

5. **[RUN]** Run the end-to-end onboarding integration test (`tests/integration/cli/test_onboarding_e2e.py`) — expected: test passes, exercising `init -> doctor -> run -> export` with mocked LLM and no manual edits between steps.

6. **[RUN]** Verify `README.md` exists at project root and contains: what rentl is, installation instructions, quickstart flow, and CLI command list.

## Results

(Appended by run-demo — do not write this section during shaping)
