# Speed with Guardrails

Fast iterations without sacrificing determinism or quality signals. Speed and quality aren't tradeoffs.

```python
# ✓ Good: Fast iteration with quality guardrails
async def edit_cycle(run_id: str, review_notes: list[ReviewNote]) -> None:
    """Apply review notes with quality guardrails."""
    # Fast: Parallel processing
    tasks = [
        apply_fix(note) for note in review_notes
    ]
    results = await asyncio.gather(*tasks)
    
    # Guardrails: Quality checks before accepting
    if not await validate_qa_after_edit(results):
        # Don't break determinism - rollback and report
        await rollback_edits(results)
        raise QualityGuardrailError(
            "Edits failed QA guardrails. "
            "Style violations: 12, "
            "Consistency issues: 3. "
            "Review manually and retry."
        )
    
    # Success: Apply and continue momentum
    await apply_edits(results)
    await emit_event("edit_cycle_completed", {
        "edits_applied": len(results),
        "qa_passed": True,
        "duration_s": 2.3  # Fast iteration
    })

# ✓ Good: Hotfix loop with guardrails
async def hotfix_fix(issue: IssueReport) -> None:
    """Fix issue rapidly but maintain quality."""
    # Speed: Targeted fix
    fix = await generate_fix(issue)
    
    # Guardrails: Validate fix doesn't break similar lines
    similar_lines = await find_similar_lines(issue.context)
    for line in similar_lines:
        if not await validate_fix_preserves_context(line, fix):
            raise QualityGuardrailError(
                f"Fix breaks context for line {line.id}. "
                "Review fix and retry."
            )
    
    # Success: Apply fast but safe
    await apply_fix(issue, similar_lines)
    await emit_event("hotfix_applied", {
        "issue_id": issue.id,
        "lines_affected": len(similar_lines) + 1,
        "qa_passed": True
    })

# ✗ Bad: Speed without guardrails
async def edit_cycle(run_id: str, review_notes: list[ReviewNote]) -> None:
    """Apply review notes - fast but breaks quality."""
    # Fast: No validation
    for note in review_notes:
        fix = await generate_fix(note)
        await apply_fix(fix)  # Apply immediately, no QA check
    
    # No guardrails - breaks determinism and consistency
    # Style violations accumulate
    # Context breaks happen silently
    # Can't roll back if issues occur
```

**Speed principles:**
- **Parallel processing:** Run independent operations concurrently (e.g., multiple edit fixes at once)
- **Targeted operations:** Fix specific issues rather than re-running entire pipeline
- **Minimal rework:** Apply fixes directly, don't require full re-translation
- **Momentum preservation:** Each iteration should improve quality without requiring manual intervention

**Quality guardrails must enforce:**
- **Style consistency:** Fixes don't break established tone or style
- **Terminology:** Fixes maintain glossary and term consistency
- **Context preservation:** Fixes don't break scene context or character consistency
- **No regressions:** New fixes don't break existing correct translations

**Guardrail enforcement:**
- **Pre-apply validation:** Check quality before accepting changes
- **Rollback capability:** Revert changes if guardrails fail
- **Clear reporting:** Explain why guardrails rejected a change
- **Fast feedback:** Validation completes quickly (not blocking speed)

**Hotfix vs regular iterations:**
- **Hotfixes:** Targeted fixes with guardrails; can use `--fast` flag (future feature for emergency only)
- **Regular edits:** Full QA cycle with all guardrails; maintain quality at speed

**Never:**
- Bypass QA checks for speed (breaks determinism and trust)
- Apply edits that fail style or terminology guardrails
- Break context without validation
- Accumulate style violations in name of "speed"

**Why:** Enables rapid iteration cycles for quality improvement while maintaining reliability through quality checks; prevents breakage from rushed changes.
