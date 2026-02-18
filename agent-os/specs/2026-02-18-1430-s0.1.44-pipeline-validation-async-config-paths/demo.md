# Demo: Pipeline Validation, Async Correctness & Config Paths

This spec hardens the pipeline with four categories of fixes: edit output validation, schema-based test assertions, async I/O correctness, and config path resolution. The demo proves each category works by exercising the affected code paths and verifying the fixes don't break anything.

## Environment

- API keys: none required
- External services: none required
- Setup: none beyond standard dev environment

## Steps

1. **[RUN]** Run `make all` — expected: all format, lint, type, unit, integration, and quality checks pass
2. **[RUN]** Verify edit output validation gate exists in orchestrator — expected: grep/inspect `orchestrator.py` confirms a validation step between merge and persistence, with rollback on failure
3. **[RUN]** Run unit tests for config init to confirm schema validation — expected: `tests/unit/core/test_init.py` assertions use `model_validate` (not raw dict access)
4. **[RUN]** Run a targeted async correctness check — expected: grep async functions in `main.py` and `downloader.py` confirms no direct `open()`/`read()`/`write()` calls; all file I/O uses `asyncio.to_thread`
5. **[RUN]** Run doctor path resolution tests — expected: `tests/unit/core/test_doctor.py` and `tests/integration/core/test_doctor.py` pass with workspace-relative resolution
6. **[RUN]** Verify agent path resolver rejects absolute paths outside workspace — expected: test or code inspection confirms `wiring.py` raises an error for paths escaping workspace

## Results

(Appended by run-demo — do not write this section during shaping)
