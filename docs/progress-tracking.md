# Progress Tracking Integration

This document describes where to emit progress updates and how to map them to the
schemas in `packages/rentl-schemas/src/rentl_schemas/progress.py`.

## Emission touchpoints

Emit progress updates at these points for every phase:

- Phase start: `phase_started`
- Milestone updates: `phase_progress`
- Phase completion: `phase_completed`
- Phase failure: `phase_failed`

At the run level, emit:

- `run_started`
- `run_completed`
- `run_failed`

## Progress payloads

- CLI/API responses should return `ApiResponse[ProgressSnapshot]` with the latest
  `RunProgress` and phase summaries.
- JSONL logs should set `LogEntry.event` to the event name and include a
  `ProgressUpdate` payload in `LogEntry.data`.

## Metrics and units

Use `ProgressMetric` entries to express phase-specific work:

- Context: `scenes_summarized` (SCENES), `characters_profiled` (CHARACTERS)
- Pretranslation: `lines_annotated` (LINES)
- Translate: `lines_translated` (LINES)
- QA: `lines_checked` (LINES), `issues_found` (ISSUES), `issues_resolved` (ISSUES)
- Edit: `lines_edited` (EDITS), `issues_resolved` (ISSUES)

If a phase needs a new unit type, add it to `ProgressUnit` and document the
metric key in the phase agent that emits it.

## Monotonic percent rules

- Do not emit percent values unless they are stable and non-decreasing.
- Use `ProgressTotalStatus.LOCKED` with `ProgressPercentMode.FINAL` when totals
  are fully known.
- For discovery or estimates, keep `percent_complete` unset and use counts only.
- `validate_progress_monotonic` can be used to enforce monotonic updates between
  snapshots before emitting them.
