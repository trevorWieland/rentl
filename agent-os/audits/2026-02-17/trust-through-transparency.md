---
standard: trust-through-transparency
category: ux
score: 82
importance: High
violations_count: 3
date: 2026-02-17
status: violations-found
---

# Standards Audit: Trust Through Transparency

**Standard:** `ux/trust-through-transparency`
**Date:** 2026-02-17
**Score:** 82/100
**Importance:** High

## Summary

Core pipeline orchestration and phase logging are largely transparent: runs and phases emit start/progress/failure events, and failures are logged with machine-readable code/next action metadata. However, three gaps remain: two UX-level paths hide progress/context (non-interactive runs and watcher error fallback) and one core retry path suppresses per-attempt visibility.

## Violations

### Violation 1: No phase progress visibility during non-interactive command execution

- **File:** `services/rentl-cli/src/rentl/main.py:936`
- **Severity:** Medium
- **Evidence:**
  ```python
  interactive = _should_render_progress()
  if interactive:
      progress = _build_progress(console)
      reporter = _ProgressReporter(bundle.progress_sink, progress, console)
  ...
  if progress is not None:
      with progress:
          result = asyncio.run(_run_pipeline_async(...))
  else:
      result = asyncio.run(_run_pipeline_async(...))
  ```
- **Recommendation:** Keep a lightweight status reporter active in non-tty runs (e.g., stderr or periodic log summaries) so command progress is never silent during long phases.

### Violation 2: Watcher exits with failed status without user-readable failure context after stale state window

- **File:** `services/rentl-cli/src/rentl/main.py:3137`
- **Severity:** Medium
- **Evidence:**
  ```python
  if no_state_count > max_no_state_iterations:
      warning_result = _build_no_state_warning_result(
          run_id, status_result, no_state_count
      )
      live.update(_build_status_panel(warning_result))
      final_status = RunStatus.FAILED
      break
  ```
  and
  ```python
  def _build_no_state_warning_result(...):
      if base_result.run_state is None:
          return replace(base_result, status=RunStatus.FAILED, run_state=None)
  ```
- **Recommendation:** Preserve a synthetic error payload (`error_code`, `why`, `next_action`) when no-state timeout triggers so users can explain and recover from what happened.

### Violation 3: Retry attempts are hidden (no progress/event emissions per retry)

- **File:** `packages/rentl-core/src/rentl_core/llm/connection.py:198`
- **Severity:** Medium
- **Evidence:**
  ```python
  while attempts < max_attempts:
      attempts += 1
      try:
          response = await runtime.run_prompt(request, api_key=api_key)
      except Exception as exc:
          last_error = _format_error(exc)
          if attempts >= max_attempts:
              break
          await asyncio.sleep(min(delay, retry.max_backoff_s))
          delay = min(delay * 2, retry.max_backoff_s)
  ```
- **Recommendation:** Emit attempt-level progress/log events (attempt index, reason, backoff duration, next action) so transient retry behavior is transparent in UI/status outputs.

## Compliant Examples

- `packages/rentl-core/src/rentl_core/orchestrator.py:382` — `RUN_STARTED` is emitted before the phase loop and `RUN_COMPLETED` after successful completion.
- `packages/rentl-core/src/rentl_core/orchestrator.py:447`–`495` and `546`–`558` — phases emit explicit `PHASE_STARTED`, `PHASE_PROGRESS`, and `PHASE_COMPLETED` events with per-phase payloads.
- `packages/rentl-core/src/rentl_core/orchestrator.py:1255`–`1316` — `_emit_phase_failure` emits `why` and `next_action` details and updates both phase and run failure state.
- `services/rentl-cli/src/rentl/main.py:1811`–`1863` — interactive progress rendering uses phase progress metrics and ETA from `rich` for visible phase progress.

## Scoring Rationale

- **Coverage:** About 80–85% of pipeline and status transitions are covered with explicit start/progress/failure events; critical runtime metadata (`error_code`, `next_action`) is present in phase failures.
- **Severity:** Violations are Medium and affect user visibility and trust during execution edge cases rather than deterministic data correctness.
- **Trend:** No clear evidence of improving trend for this standard in the reviewed paths; the same transparency gaps are present in both run path and status/watch recovery path.
- **Risk:** Moderate: silent stalls can reduce diagnosability and confidence in long-running runs.

