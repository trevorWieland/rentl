---
standard: copy-pasteable-examples
category: ux
score: 43
importance: High
violations_count: 59
date: 2026-02-17
status: violations-found
---

# Standards Audit: Copy-Pasteable Command Examples

**Standard:** `ux/copy-pasteable-examples`
**Date:** 2026-02-17
**Score:** 43/100
**Importance:** High

## Summary

The codebase still contains many non-copy-pasteable command examples with `<...>` placeholders, especially in workflow, spec, and draft process docs. The biggest gap is variable-style placeholders in commands rather than runtime-ready values (paths, commands, and arguments). A few user-facing docs now include concrete examples (`docs/getting-started.md`), and the dedicated standard file explicitly documents a compliant pattern, but enforcement is not yet consistent across repo documentation.

## Violations

### Violation 1: Placeholder command placeholders in user help examples

- **File:** `README.md:132`
- **Severity:** High
- **Evidence:**
  ```
  uvx rentl <command> --help
  ```
- **Recommendation:** Replace with a concrete entrypoint command sequence or remove in favor of explicit command list, e.g. `uvx rentl run-pipeline`, `uvx rentl status`, `uvx rentl export --help`.

### Violation 2: Placeholder command arguments in troubleshooting help guidance

- **File:** `docs/troubleshooting.md:114`
- **Severity:** High
- **Evidence:**
  ```
  `rentl <command> --help`
  ```
- **Recommendation:** Replace with explicit examples or a direct helper invocation that does not require user substitution, for example:
  ```bash
  uvx rentl run-pipeline --help
  uvx rentl status --help
  uvx rentl benchmark --help
  ```

### Violation 3: Placeholder `<spec-folder>` and config path values in contributor/setup workflows

- **File:** `CONTRIBUTING.md:94`, `CONTRIBUTING.md:124`
- **Severity:** Medium
- **Evidence:**
  ```
  ./agent-os/scripts/orchestrate.sh agent-os/specs/<your-spec-folder>
  ./agent-os/scripts/orchestrate.sh <spec-folder> --config my-config.conf
  ```
- **Recommendation:** Use an actual example path from this repo and a concrete config name, e.g. `./agent-os/scripts/orchestrate.sh agent-os/specs/2026-02-17-1536-s0141-documentation-overhaul`.

### Violation 4: Placeholder spec placeholders (`<spec-folder>`, `<your-spec-folder>`) across workflow drafts

- **File:** `agent-os/docs/draft-general.md:206`, `agent-os/docs/draft-general.md:832`, `agent-os/docs/draft-general.md:833`, `agent-os/docs/draft-general.md:1467`, `agent-os/docs/draft-educational.md:139`, `agent-os/docs/draft-educational.md:152`, `agent-os/docs/draft-educational.md:162`, `agent-os/docs/draft-educational.md:569`, `agent-os/docs/draft-educational.md:570`, `agent-os/docs/draft-educational.md:826`, `agent-os/docs/draft-concise.md:78`, `agent-os/docs/draft-concise.md:91`, `agent-os/docs/draft-concise.md:101`, `agent-os/docs/draft-concise.md:498`, `agent-os/docs/draft-concise.md:499`, `agent-os/docs/draft-concise.md:747`, `agent-os/docs/draft-complete.md:133`, `agent-os/docs/draft-complete.md:759`, `agent-os/docs/draft-complete.md:760`, `agent-os/docs/draft-complete.md:1383`, `agent-os/docs/WORKFLOW-GUIDE.md:139`, `agent-os/docs/WORKFLOW-GUIDE.md:152`, `agent-os/docs/WORKFLOW-GUIDE.md:162`, `agent-os/docs/WORKFLOW-GUIDE.md:569`, `agent-os/docs/WORKFLOW-GUIDE.md:570`, `agent-os/docs/WORKFLOW-GUIDE.md:826`
- **Severity:** Medium
- **Evidence:**
  ```
  ./agent-os/scripts/orchestrate.sh <spec-folder>
  ./agent-os/scripts/orchestrate.sh <spec-folder> --config orchestrate.conf
  ```
- **Recommendation:** Provide one concrete path and command example each time (or a shell snippet that prints valid candidate paths before calling the script).

### Violation 5: Placeholder placeholders in branch and path references within workflow guidance

- **File:** `agent-os/docs/draft-general.md:1065`, `agent-os/docs/draft-educational.md:459`, `agent-os/docs/draft-concise.md:390`, `agent-os/docs/draft-complete.md:979`, `agent-os/docs/WORKFLOW-GUIDE.md:459`, `agent-os/product/roadmap.md:59`
- **Severity:** Medium
- **Evidence:**
  ```
  gh pr list --head <branch-name>
  rentl explain <phase>
  ```
- **Recommendation:** Replace with concrete examples that use an existing branch and a valid phase name, or provide commands that derive these values in-shell.

### Violation 6: Placeholder placeholders in command signatures in specs/audit notes

- **File:** `agent-os/specs/2026-02-07-1930-s0131-cli-help-doctor-commands/spec.md:15`, `agent-os/specs/2026-02-07-1930-s0131-cli-help-doctor-commands/spec.md:30`, `agent-os/specs/2026-02-07-1930-s0131-cli-help-doctor-commands/spec.md:41`, `agent-os/specs/2026-02-07-1930-s0131-cli-help-doctor-commands/spec.md:43`, `agent-os/specs/2026-02-11-1440-s0130-onboarding-docs-pack/demo.md:15`, `agent-os/specs/2026-02-11-1440-s0130-onboarding-docs-pack/audit.md:21`
- **Severity:** Medium
- **Evidence:**
  ```
  rentl help <command>
  uv run rentl <command> --help
  ```
- **Recommendation:** Keep this standard in spec docs by adding concrete sample invocations (e.g., `rentl help benchmark`, `uv run rentl status`) for each required behavior.

### Violation 7: Placeholder input/output paths in benchmark documentation workflows

- **File:** `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/spec.md:33`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/spec.md:34`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:17`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:160`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/plan.md:199`, `agent-os/specs/2026-02-09-2017-s0137-benchmark-harness/audit.md:22`
- **Severity:** Medium
- **Evidence:**
  ```
  rentl benchmark compare <output-a> <output-b>
  uv run rentl benchmark download ... --output-dir <tmp>
  ```
- **Recommendation:** Replace placeholders with realistic sample paths or show a full shell sequence producing outputs from local files first.

### Violation 8: Placeholder package and build/runtime names in planning docs

- **File:** `agent-os/specs/2026-02-11-1830-s0.1.39-install-verification/plan.md:29`, `agent-os/specs/2026-02-17-1536-s0141-documentation-overhaul/plan.md:32`
- **Severity:** Medium
- **Evidence:**
  ```
  uv build --package <name> --no-sources
  uvx rentl export -i out/run-<run-id>/en.jsonl ...
  ```
- **Recommendation:** Provide copy-paste examples with explicit package names and concrete artifact paths generated in the guide.

### Violation 9: Placeholder path in onboarding signpost/audit evidence

- **File:** `agent-os/specs/2026-02-11-1440-s0130-onboarding-docs-pack/signposts.md:8`, `agent-os/specs/2026-02-11-1440-s0130-onboarding-docs-pack/plan.md:28`, `agent-os/specs/2026-02-11-1440-s0130-onboarding-docs-pack/plan.md:29`
- **Severity:** Medium
- **Evidence:**
  ```
  --input <translated-lines-jsonl>
  --input <translated-lines-jsonl-from-status>
  ```
- **Recommendation:** Replace with status-derived path flow, for example use `RUN_DIR=...` and then `rentl export --input "$RUN_DIR/edited_lines.jsonl" --output "$RUN_DIR/translations.csv" --format csv`.

### Violation 10: Standard file contains an intentional bad example

- **File:** `agent-os/standards/ux/copy-pasteable-examples.md:10`
- **Severity:** Medium
- **Evidence:**
  ```
  uv run rentl export --input <translated-lines.jsonl> --output translations.csv --format csv
  ```
- **Recommendation:** Keep this file’s bad example as explanatory text only if clearly labeled as invalid (it is currently labeled as bad); no additional change needed unless this line is meant to be copy-paste usage in the doc.

### Violation 11: Branch/path template placeholders in docs tables and command metadata

- **File:** `agent-os/docs/draft-educational.md:521`, `agent-os/docs/draft-concise.md:452`, `agent-os/docs/WORKFLOW-GUIDE.md:521`
- **Severity:** Medium
- **Evidence:**
  ```
  `agent-os/standards/<topic>/<name>.md`
  ```
- **Recommendation:** Replace with concrete file references where practical, or add a shell snippet that selects a valid example file instead of placeholder angle brackets.

## Compliant Examples

- `docs/getting-started.md:20-25` — Uses executable setup and verify commands with concrete flags.
- `agent-os/standards/ux/copy-pasteable-examples.md:7` — Provides a copy-pasteable export example with explicit paths.
- `docs/getting-started.md:171-173` — Pipeline command example has no placeholders.

## Scoring Rationale

- **Coverage:** Approximately 59 placeholder command examples were found; only a small subset (about 8 in this sample set) were already concrete and executable, so coverage is low.
- **Severity:** Most issues are Medium, but they are High-impact for user onboarding where top-level help examples require immediate execution.
- **Trend:** Recent onboarding docs (`docs/getting-started.md`) show better compliance than older draft/spec artifacts, indicating partial progress.
- **Risk:** High operational risk for documentation users because many commands cannot be copy-pasted and require manual edits, which is exactly the friction this standard is intended to prevent.
