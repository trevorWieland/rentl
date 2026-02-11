# Signposts

## Task 3 - Quick Start export workflow is still not executable

- **Task:** 3
- **Status:** unresolved
- **Problem:** README Quick Start still does not provide an end-to-end copy-pasteable export path after `run-pipeline`.
- **Evidence:** `README.md:103-107` describes manual transformation steps without commands, and `README.md:113` uses placeholder input `--input <translated-lines.jsonl>`. This violates the zero-to-pipeline requirement in `spec.md:38`.
- **Impact:** New users can complete pipeline execution but cannot complete export without reverse-engineering data transformation, increasing onboarding friction and causing repeated audit failures.
