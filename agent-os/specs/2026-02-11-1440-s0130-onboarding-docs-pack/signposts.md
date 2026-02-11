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
