# Signposts

## Task 3 - Quick Start export workflow is still not executable

- **Task:** 3
- **Status:** resolved
- **Problem:** README Quick Start still does not provide an end-to-end copy-pasteable export path after `run-pipeline`.
- **Evidence:** `README.md:103-107` describes manual transformation steps without commands, and `README.md:113` uses placeholder input `--input <translated-lines.jsonl>`. This violates the zero-to-pipeline requirement in `spec.md:38`.
- **Solution:** Added concrete command sequence using `jq` to extract the edit phase artifact, transform EditPhaseOutput to TranslatedLine JSONL, and execute export with the generated file. Commands use `rentl status --json` to get artifact path, `jq` to extract and transform data, and `rentl export` to produce final output.
- **Resolution:** do-task round 4, 2026-02-11
- **Files affected:** `README.md:97-116`
- **Impact:** New users can complete pipeline execution but cannot complete export without reverse-engineering data transformation, increasing onboarding friction and causing repeated audit failures.

## Task 4 - Troubleshooting doc hardcodes stale API key env var

- **Task:** 4
- **Status:** resolved
- **Problem:** The Missing API Key section uses a hardcoded env var name (`RENTL_API_KEY`) that does not match the current configuration model.
- **Evidence:** `docs/troubleshooting.md:27` says `RENTL_API_KEY=your-api-key-here`, but `rentl.toml.example:33` defines `api_key_env = "RENTL_LOCAL_API_KEY"` and `.env.example:2` documents `RENTL_LOCAL_API_KEY`.
- **Solution:** Updated the Missing API Key fix section to instruct users to check their `rentl.toml` for the `api_key_env` value first, then set that variable in `.env`. Used `RENTL_LOCAL_API_KEY` as the example to match the current config examples.
- **Resolution:** do-task round 2, 2026-02-11
- **Files affected:** `docs/troubleshooting.md:23-30`
- **Impact:** Users following troubleshooting guidance may set the wrong key, causing repeated auth failures and violating the spec non-negotiable on stale references.
