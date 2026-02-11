spec_id: s0.1.22
issue: https://github.com/trevorWieland/rentl/issues/23
version: v0.1

# Spec: Functional Onboarding

## Problem

The individual onboarding pieces exist (`rentl init`, `rentl doctor`, `rentl help`, `rentl explain`) but the end-to-end path from zero to first successful run has gaps. Doctor doesn't load `.env` files (so API key checks fail even when the key is set), init only offers one hardcoded provider (OpenRouter with raw URL entry), the pipeline summary doesn't guide users to export, and there's no README for first-time visitors to orient themselves.

## Goals

- Make the `init -> doctor -> run-pipeline -> export` flow seamless with no manual edits required (given a valid API key)
- Surface actionable guidance at every step so users never wonder "what now?"
- Provide a project README that orients first-time visitors

## Non-Goals

- Exhaustive documentation or tutorials (that's s0.1.30: Onboarding Docs Pack)
- TUI onboarding experience (that's v0.5)
- Onboarding context building / user interviews (that's s0.2.20)

## Acceptance Criteria

- [ ] `rentl doctor` loads `.env` (and `.env.local`) from the config directory before running checks, so API keys set in `.env` are visible to the API key and connectivity checks
- [ ] `rentl init` offers at least 3 provider presets (OpenRouter, OpenAI, local/Ollama) that pre-fill base URL, API key env var, and a default model; users can still enter custom values
- [ ] `rentl init` validates the base URL format before accepting it (rejects non-URL strings)
- [ ] After `rentl run-pipeline` completes successfully, the summary includes clear next steps: the export command to run and the output path where translated files will appear
- [ ] An integration test exercises the full `init -> doctor -> run-pipeline -> export` flow with a mocked LLM, verifying the generated project runs without manual edits
- [ ] All doctor check failure messages reference `.env` loading and provide copy-pasteable fix commands
- [ ] A root-level `README.md` exists with: what rentl is (brief pitch), installation instructions (uv/uvx), quickstart flow (`init -> doctor -> run-pipeline -> export`), and a list of available CLI commands
- [ ] All tests pass including full verification gate (`make all`)
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Init output must be immediately runnable** — The generated `rentl.toml` + seed data must pass `rentl doctor` and complete `rentl run-pipeline` without any manual file edits (given a valid API key in the environment). If init produces config that requires hand-editing to run, this spec fails.
2. **No silent failures during first run** — Every error encountered during `init -> doctor -> run-pipeline -> export` must surface an actionable message with a fix suggestion. No swallowed exceptions, no empty output, no cryptic tracebacks.
3. **Doctor must catch all first-run blockers** — If doctor reports all-pass, the subsequent `rentl run-pipeline` must not fail due to configuration, connectivity, or environment issues. Doctor is the gatekeeper: if it passes, the pipeline runs.
4. **Init-generated config must round-trip validate** — The TOML produced by `generate_project()` must parse back into a valid `RunConfig` and pass schema validation. No drift between the template and the consuming schema.
