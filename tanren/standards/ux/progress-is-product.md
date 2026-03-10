# Progress is the Product

Status, phase completion, and QA visibility must be immediate and unambiguous. Progress is the product, not a feature.

```python
# ✓ Good: Immediate, unambiguous progress updates
async def run_pipeline(run_id: str) -> None:
    """Run pipeline with visible progress."""
    # Phase 1: Ingest
    await emit_event("phase_started", {"phase": "ingest", "status": "running"})
    await ingest_phases(config)
    await emit_event("phase_completed", {"phase": "ingest", "lines": 1234, "duration_s": 2.3})
    
    # Phase 2: Context
    await emit_event("phase_started", {"phase": "context", "status": "running"})
    await context_phases(config)
    await emit_event("phase_completed", {"phase": "context", "scenes_processed": 50, "duration_s": 8.7})

# ✓ Good: CLI status command shows clear state
$ rentl show-status abc123
✓ Phase: translate (60% complete)
  - Lines processed: 750/1250
  - ETA: 2m 15s

# ✗ Bad: Ambiguous or delayed progress
async def run_pipeline(run_id: str) -> None:
    """Run pipeline with poor visibility."""
    # Silent ingestion, no updates
    await ingest_phases(config)
    # Silent context, no updates
    await context_phases(config)
    # Only shows progress at the very end
    await translate_phases(config)

# ✗ Bad: CLI status unclear
$ rentl show-status abc123
Running...
[No progress indicators, no phase information]
```

**Progress visibility requirements:**
- **Immediate:** Emit progress events at phase start, completion, and meaningful milestones
- **Unambiguous:** Clear phase name, status (running/completed/failed), and completion percentage
- **Granular enough:** Show line counts, token usage, or scene counts where applicable
- **ETA indicators:** Show estimated time remaining for long-running phases
- **Error visibility:** Failed lines or scenes are immediately visible, not buried at the end

**Progress by phase:**
- `phase_started` event with phase name and status
- Milestone updates within phase (e.g., every 100 lines translated)
- `phase_completed` event with completion metrics (lines processed, duration)
- `phase_failed` event with error context (what failed, why)

**Status indicators (CLI/TUI):**
- Phase name and status clearly visible
- Progress percentage or fraction (e.g., "750/1250 lines")
- Time elapsed and ETA
- Active animation or spinner for running phases
- Error messages inline with phase context

**Exceptions (brief initialization):**
Only during brief initialization (config loading, establishing connections) can have delayed/ambiguous progress. Emit initial status within 5 seconds or show "Initializing..." with clear startup phase name.

**Why:** Builds trust by showing what's done, what's next, and what failed; creates visible momentum and sense of progress; prevents "black box" anxiety where users don't know if things are working.
