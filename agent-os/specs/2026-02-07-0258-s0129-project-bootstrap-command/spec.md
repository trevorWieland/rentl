spec_id: s0.1.29
issue: https://github.com/trevorWieland/rentl/issues/29
version: v0.1

# Spec: Project Bootstrap Command

## Problem

There is no `rentl init` command. Users must manually copy `rentl.toml.example`, edit every field, create directories, and set up environment variables before running their first pipeline. This friction violates the "frictionless by default" UX standard and makes the first-run experience intimidating for fan translators.

## Goals

- Add `rentl init` as an interactive interview-style CLI command that scaffolds a ready-to-run project
- Generate a valid `rentl.toml`, `.env` template, workspace directories, and optional seed data
- Minimize time-to-first-run: after init + setting an API key, the pipeline should work immediately
- Structure the init system for future expansion (s0.2.20)

## Non-Goals

- Copier template integration (separate concern, potentially s0.2.20)
- Git repository initialization (users handle this themselves)
- Custom agent/prompt creation during init (default agents are sufficient for v0.1)
- Multi-endpoint configuration during init (single endpoint is sufficient for bootstrap)

## Acceptance Criteria

- [ ] `rentl init` command exists and is registered in the CLI
- [ ] Running `rentl init` in an empty directory interactively prompts for: project name, game name, source language, target language(s), endpoint provider name, base URL, API key env var name, model ID, and input format
- [ ] After the interview, init creates: `rentl.toml` (valid config), `.env` (API key placeholder), workspace directories (`input/`, `out/`, `logs/`), and an optional seed sample file
- [ ] The generated `rentl.toml` passes `validate_run_config()` without modification (except for the API key env var value)
- [ ] Init prints a summary of created files and next-step instructions
- [ ] Running `rentl init` in a directory with an existing `rentl.toml` warns and asks for confirmation before overwriting
- [ ] All prompts have sensible defaults so users can press Enter through quickly
- [ ] The interview logic and template generation live in `rentl-core`, not in the CLI layer
- [ ] `[agents]` config section is optional — runtime falls back to package defaults when omitted
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **Generated config must validate** — The output `rentl.toml` must pass `validate_run_config()` without modification (except for the API key env var placeholder). If the generated config fails validation, the spec fails.
2. **No hardcoded provider assumptions** — Init must support any OpenAI-compatible endpoint, not just OpenRouter or a specific provider. The interview asks for provider name, base URL, and API key env var.
3. **Thin adapter pattern** — The `init` CLI command delegates to a core domain function in `rentl-core`. No business logic (config generation, file creation, validation) in the CLI layer.
4. **Generated project must be runnable** — After init + setting an API key, `rentl run-pipeline` must work against the generated project without manual config edits.
5. **Full scaffold with guidance** — Init creates all workspace directories (input, output, logs) and prints clear next-step instructions (e.g., "put your input data into ./input").
6. **Interview-style prompts** — Init interactively asks for project name, game name, source language, target languages, endpoint config, and input format. Each prompt has a sensible default.
7. **Extensible design** — The init interview and template generation must be structured (Pydantic models for answers/results, separate generation function) so new questions/options can be added in future specs (s0.2.20) without rewriting the core.
