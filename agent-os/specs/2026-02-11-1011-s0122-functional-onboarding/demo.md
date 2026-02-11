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

### Run 1 — Initial onboarding flow (2026-02-11 11:59)
- Step 1 [RUN]: **PASS** — `rentl init` successfully created project structure with rentl.toml, .env, seed data, and workspace directories (input/, out/, logs/). Provider menu offered OpenRouter, OpenAI, and Local/Ollama presets as expected.
- Step 2 [RUN]: **FAIL** — `rentl doctor` connectivity check failed. API key was correctly loaded from .env (5/6 checks passed), but LLM connectivity test failed with: `status_code: 404, model_name: openai/gpt-4.1, body: {'message': 'No endpoints found that can handle the requested parameters...'}`. Root cause: OpenRouter preset uses invalid model ID "openai/gpt-4.1" which does not exist on OpenRouter.
- Step 3 [RUN]: **SKIPPED** — Cannot proceed without working configuration from Step 2.
- Step 4 [RUN]: **SKIPPED** — Cannot proceed without working configuration from Step 2.
- Step 5 [RUN]: **SKIPPED** — Cannot proceed without working configuration from Step 2.
- Step 6 [RUN]: **SKIPPED** — Cannot proceed without working configuration from Step 2.
- **Overall: FAIL**

### Run 2 — After preset model ID fix (2026-02-11 12:20)
- Step 1 [RUN]: **PASS** — `rentl init` created all expected files and directories (rentl.toml, .env, input/, out/, logs/). Seed data file generated. Provider menu offered 3 presets plus Custom option.
- Step 2 [RUN]: **PASS** — `rentl doctor` passed all 6 checks (Python version, config file, config valid, workspace dirs, API keys, LLM connectivity). API key correctly loaded from .env.
- Step 3 [RUN]: **FAIL** — `rentl run-pipeline` failed with validation error: `{"error":{"code":"untranslated_text","message":"3 export errors; first: line 1: Translated text matches source text"}}`. Root cause: Init-generated seed data is in English ("Example dialogue line 1"), but config specifies source language as Japanese (ja). LLM correctly refuses to "translate" English→English text, triggering export validation failure.
- Step 4 [RUN]: **SKIPPED** — Cannot proceed without successful pipeline run from Step 3.
- Step 5 [RUN]: **PASS** — E2E integration test passed (pytest tests/integration/cli/test_onboarding_e2e.py). Test uses mocked LLM responses so seed data language mismatch doesn't affect it.
- Step 6 [RUN]: **PASS** — README.md exists with all required sections (Installation, Quick Start, Available Commands, License).
- **Overall: FAIL**

### Run 3 — After seed data language fix (2026-02-11 12:32)
- Step 1 [RUN]: **PASS** — `rentl init` successfully created project structure with all expected files (rentl.toml, .env, input/, out/, logs/) and seed data file. Provider menu offered 3 presets (OpenRouter, OpenAI, Local/Ollama) plus Custom option. Seed data generated in Japanese ("サンプル台詞 1", "サンプル台詞 2", "サンプル台詞 3") matching configured source language ja.
- Step 2 [RUN]: **PASS** — `rentl doctor` passed all 6 checks (Python version, config file, config valid, workspace dirs, API keys, LLM connectivity). API key correctly loaded from .env before checks ran.
- Step 3 [RUN]: **PASS** — `rentl run-pipeline` completed successfully across all phases (ingest → context → pretranslation → translate → qa → edit → export). Run ID: 019c4dfa-b4f5-7676-ae5d-8fcb44390118. Pipeline processed 3 lines (ja → en) with 0 QA issues. Export output created at out/run-019c4dfa-b4f5-7676-ae5d-8fcb44390118/en.jsonl with translated content.
- Step 4 [RUN]: **PASS** — `rentl export` successfully exported translated lines to CSV format. Exported 3 lines with no untranslated content. Output file created at specified path.
- Step 5 [RUN]: **PASS** — E2E onboarding integration test passed (pytest tests/integration/cli/test_onboarding_e2e.py). Test exercised full `init -> doctor -> run-pipeline -> export` flow with mocked LLM and no manual edits between steps.
- Step 6 [RUN]: **PASS** — README.md exists at project root with all required sections: what rentl is (pitch), installation instructions (uv/uvx), quickstart flow (init → doctor → run-pipeline → export), CLI command list, and license link.
- **Overall: PASS**

### Run 4 — Final verification (2026-02-11 12:53)
- Step 1 [RUN]: **PASS** — `rentl init` successfully created project structure with rentl.toml, .env, input/, out/, logs/, and seed data file (input/test-project.jsonl). Provider menu offered 3 presets (OpenRouter, OpenAI, Local/Ollama) plus Custom option. Seed data generated in Japanese ("サンプル台詞 1", "サンプル台詞 2", "サンプル台詞 3") matching configured source language ja.
- Step 2 [RUN]: **PASS** — `rentl doctor` passed all 6 checks (Python version, config file, config valid, workspace dirs, API keys, LLM connectivity). API key correctly loaded from .env before checks ran.
- Step 3 [RUN]: **PASS** — `rentl run-pipeline` completed successfully across all phases (ingest → context → pretranslation → translate → qa → edit → export). Run ID: 019c4e0d-4fb2-773f-8b52-8a6036c0e769. Pipeline processed 3 lines (ja → en) with 0 QA issues. Export output created at out/run-019c4e0d-4fb2-773f-8b52-8a6036c0e769/en.jsonl with translated content ("Sample line 1", "Sample line 2", "Sample line 3").
- Step 4 [RUN]: **PASS** — `rentl export` successfully exported translated lines to CSV format. Exported 3 lines with no untranslated content. Output file created at demo-export.csv with line_id and text columns.
- Step 5 [RUN]: **PASS** — E2E onboarding integration test passed (pytest tests/integration/cli/test_onboarding_e2e.py). Test exercised full `init -> doctor -> run-pipeline -> export` flow with mocked LLM and no manual edits between steps.
- Step 6 [RUN]: **PASS** — README.md exists at project root with all required sections: pitch ("An open-source, BYOK agentic localization pipeline..."), installation instructions (uv/uvx), quickstart flow (init → doctor → run-pipeline → export), CLI command list, and license link to LICENSE file.
- **Overall: PASS**
