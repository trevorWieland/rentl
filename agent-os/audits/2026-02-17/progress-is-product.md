---
standard: progress-is-product
category: ux
score: 82
importance: Medium
violations_count: 3
date: 2026-02-17
status: violations-found
---

# Standards Audit: Progress is the Product

**Standard:** `ux/progress-is-product`
**Date:** 2026-02-17
**Score:** 82/100
**Importance:** Medium

## Summary

Most of the pipeline emits explicit phase lifecycle events and has structured CLI/status reporting with phase-level progress percentages, ETA, and run summaries. However, there are notable gaps in user-facing visibility during single-phase runs and for non-agent phases (`ingest`, `export`), where granular running progress is missing. Failure paths also lose context in live CLI progress output, reducing immediate error explainability.

## Violations

### Violation 1: `run-phase` has no interactive progress sink, so no live phase progression output

- **File:** `services/rentl-cli/src/rentl/main.py:1038-1085`
- **Severity:** Medium
- **Evidence:**
  ```python
  bundle = _build_storage_bundle(config, resolved_run_id, allow_console_logs=False)
  log_sink = bundle.log_sink
  if _should_render_progress():
      _render_run_start(...)
  result = asyncio.run(_run_phase_async(...))
  ```
- **Recommendation:** Mirror `run-pipeline` behavior in `run-phase` by wrapping `bundle.progress_sink` in `_ProgressReporter` and running the async call inside a Rich `Progress` context so phase start/progress/completion are visible while the command runs.

### Violation 2: Phase failure CLI output omits immediate error context

- **File:** `services/rentl-cli/src/rentl/main.py:1832-1834`, `packages/rentl-core/src/rentl_core/orchestrator.py:1247-1285`, `packages/rentl-core/src/rentl_core/orchestrator.py:3315-3323`
- **Severity:** Medium
- **Evidence:**
  ```python
  if update.event == ProgressEvent.PHASE_FAILED and update.phase is not None:
      self._console.print(f"{update.phase} failed")
  
  await self._emit_progress(run, phase, ProgressEvent.PHASE_FAILED)
  error_code, why, next_action = _build_error_payload(message, error_info)
  ```
- **Recommendation:** Emit and render failure payload context (e.g., `update.message`, `why`, `next_action`) on `PHASE_FAILED` in `_ProgressReporter` so failed lines/scenes causes are visible immediately, not only after command end or separate logs.

### Violation 3: No milestone progress for `ingest` and `export` phases

- **File:** `packages/rentl-core/src/rentl_core/orchestrator.py:564-621`, `packages/rentl-core/src/rentl_core/orchestrator.py:1083-1172`
- **Severity:** Medium
- **Evidence:**
  ```python
  async def _run_ingest(...):
      await self._emit_log(build_ingest_started_log(...))
      run.source_lines = await self._ingest_adapter.load_source(ingest_source)
      ...
      await self._emit_log(build_ingest_completed_log(...))
  
  async def _run_export(...):
      translated_lines = _select_export_lines(run, target_language)
      export_result = await self._export_adapter.write_output(export_target, translated_lines)
      ...
      await self._emit_log(build_export_completed_log(...))
  ```
- **Recommendation:** Add periodic `_emit_phase_progress_update` calls in these phases (for example, after ingest chunk loads/writes and export row writes) so status shows running fraction, percent, and ETA instead of only start/completion.

## Compliant Examples

- `packages/rentl-core/src/rentl_core/orchestrator.py:486` and `packages/rentl-core/src/rentl_core/orchestrator.py:546` emit clear `PHASE_STARTED` and `PHASE_COMPLETED` events with phase context.
- `packages/rentl-core/src/rentl_core/orchestrator.py:1239-1245` updates `phase_progress` with metric and ETA and emits `PHASE_PROGRESS` for supported phases.
- `services/rentl-cli/src/rentl/main.py:3204-3219` and `services/rentl-cli/src/rentl/main.py:3344-3351` render phase status, percent, and fraction in status output.
- `services/rentl-cli/src/rentl/main.py:1869-1876` includes ETA in active progress rendering.

## Scoring Rationale

- **Coverage:** Progress lifecycle events are present for core phases and visible through status snapshots, but three key paths reduce completeness (`run-phase` interactivity and non-agent phase milestones).
- **Severity:** All identified gaps are Medium; they affect UX transparency and fast diagnosability rather than core execution correctness.
- **Trend:** Within the reviewed files, patterns are consistent: agent-driven phases have richer milestone updates; non-agent phases and some CLI command paths are less fully instrumented.
- **Risk:** Users may see “running” phases without meaningful fractions or immediate failure context, especially for long `run-phase` executions and `ingest`/`export`, which increases operational uncertainty during long jobs.
