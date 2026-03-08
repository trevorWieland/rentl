---
standard: speed-with-guardrails
category: ux
score: 44
importance: High
violations_count: 3
date: 2026-02-17
status: violations-found
---

# Standards Audit: Speed with Guardrails

**Standard:** `ux/speed-with-guardrails`
**Date:** 2026-02-17
**Score:** 44/100
**Importance:** High

## Summary
The edit pipeline is fast and parallelized, and QA phase execution itself has strong pre-validate behavior. However, the edit phase applies edited lines directly with no post-edit quality gate and no rollback path, so quality regressions can be accepted and exported immediately.

## Violations

### Violation 1: Edit phase lacks pre-apply validation before persisting edited output

- **File:** `packages/rentl-core/src/rentl_core/orchestrator.py:1002`
- **Severity:** High
- **Evidence:**
  ```python
  merged_output = _merge_edit_outputs_across_agents(
      run, target_language, agent_outputs
  )
  run.edit_outputs[target_language] = merged_output
  artifact_ids = await self._persist_phase_artifact(
      run,
      PhaseName.EDIT,
      merged_output,
      target_language,
      description=f"Edit output ({target_language})",
  )
  ```
- **Recommendation:** Insert a pre-apply quality gate between merge and persistence (e.g., deterministic checks + at least style/terminology/context guardrails on `merged_output`), and only persist when all checks pass.

### Violation 2: No no-regression/style/terminology/context checks are enforced on edited lines after edit generation

- **File:** `packages/rentl-agents/src/rentl_agents/wiring.py:900`
- **Severity:** High
- **Evidence:**
  ```python
  for line in payload.translated_lines:
      qa_text = self._format_qa_issues(payload.qa_issues, line.line_id)
      ...
      result = await self._profile_agent.run(payload)
      if result.line_id != line.line_id:
          ... raise RuntimeError ...
      edited_text = result.text
      edited_lines.append(TranslatedLine(... text=edited_text ...))
  ```
- **Recommendation:** Add explicit post-edit validation logic in the edit agent path to verify style consistency, glossary/terminology preservation, context continuity, and unchanged lines that were not part of the targeted issue.

### Violation 3: Edit outputs are exported without any subsequent validation path

- **File:** `packages/rentl-core/src/rentl_core/orchestrator.py:2990`
- **Severity:** Medium
- **Evidence:**
  ```python
  def _select_export_lines(...):
      if target_language in run.edit_outputs:
          return run.edit_outputs[target_language].edited_lines
      if target_language in run.translate_outputs:
          return run.translate_outputs[target_language].translated_lines
  ```
- **Recommendation:** Add a mandatory post-edit QA gate (or policy-controlled optional gate) before export promotion so the final output cannot bypass `edit`-phase regressions.

## Compliant Examples

- `packages/rentl-core/src/rentl_core/orchestrator.py:191-223` — `PhaseAgentPool.run_batch` runs payloads concurrently with `asyncio.TaskGroup` and semaphore-backed parallelism.
- `packages/rentl-core/src/rentl_core/orchestrator.py:1877-1901` — `PhaseWorkStrategy` chunking supports targeted incremental work units instead of full reprocessing.
- `packages/rentl-core/src/rentl_core/orchestrator.py:905-976` — QA phase performs deterministic checks before agent QA and merges deterministic+LLM findings before persistence.
- `packages/rentl-agents/src/rentl_agents/wiring.py:942-950` — Edit agent retries and rejects when edited line_id is misaligned, preserving deterministic line contract.

## Scoring Rationale

- **Coverage:** Only about half of the standard’s intent is covered: execution is parallel and targeted, but no edit-stage quality gate exists.
- **Severity:** High-severity issues exist because edited output can be accepted and exported without revalidation, creating correctness risk.
- **Trend:** Current implementation favors throughput over deterministic quality enforcement in the edit stage.
- **Risk:** High practical risk of style, terminology, and context regressions entering the final artifact without rollback protection.
