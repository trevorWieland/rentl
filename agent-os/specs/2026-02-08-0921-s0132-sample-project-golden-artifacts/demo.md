# Demo: Sample Project + Golden Artifacts

rentl now ships with a bundled sample project — an original Japanese visual novel script with pre-validated golden artifacts for every pipeline phase. This means new users can see what the pipeline produces before configuring their own project, and developers have a reliable fixture for smoke tests and integration testing.

## Steps

1. **Show the sample script exists and is well-formed** — Load `samples/golden/script.jsonl`, print line count, show a few lines with different speakers and narration. Expected: valid JSONL with multiple scenes, routes, and speakers including dialogue, narration, choices, and `"???"` speaker lines.

2. **Validate all golden artifacts against schemas** — Run the unit validation test suite (`pytest tests/unit/test_golden_artifacts.py -v`). Expected: every artifact file (context, pretranslation, translate, QA, edit, export) parses without errors.

3. **Run the full pipeline on the sample script** — Execute `rentl run` (or the pipeline integration test) on the sample project with the default config. Expected: all phases (ingest → context → pretranslation → translate → QA → edit → export) complete without errors.

4. **Ingest round-trip validation** — Run the ingest integration test. Expected: ingesting `script.jsonl` through the JSONL adapter produces SourceLine records matching the golden data.

5. **Verify the full test suite passes** — Run `make all`. Expected: all tests pass, including the new golden artifact and pipeline smoke tests.

6. **Confirm sample_scenes.jsonl is gone** — Run `git grep sample_scenes.jsonl` and check the filesystem. Expected: zero references, file deleted, `rentl.toml` points to `samples/golden/script.jsonl`.

7. **Confirm the license** — Show the license file at `samples/golden/LICENSE`. Expected: CC0 or equivalent permissive license explicitly stated.

## Results

### Run 1 — Full pipeline validation (2026-02-08 19:30)
- Step 1: PASS — Script has 58 lines with multiple speakers (???, 佐藤健太, 美咲), dialogue, and narration
- Step 2: PASS — All 7 golden artifact validation tests passed in 0.20s
- Step 3: PASS — Full verification gate (`make all`) passed: 626 unit tests, 61 integration tests, 5 quality tests
- Step 4: PASS — Ingest integration test passed in 0.02s
- Step 5: PASS — Covered by Step 3
- Step 6: PASS — Zero operational references to sample_scenes.jsonl, file deleted
- Step 7: PASS — CC0 1.0 Universal license present at samples/golden/LICENSE
- **Overall: PASS**

### Run 2 — Post-audit verification (2026-02-08 20:15)
- Step 1: PASS — Script has 58 lines with multiple speakers (???, 佐藤健太, 美咲), dialogue, and narration
- Step 2: PASS — All 7 golden artifact validation tests passed in 0.24s
- Step 3: PASS — Full verification gate (`make all`) passed: 626 unit tests, 61 integration tests, 5 quality tests
- Step 4: PASS — Ingest integration test passed in 0.02s
- Step 5: PASS — Covered by Step 3
- Step 6: PASS — Zero operational references to sample_scenes.jsonl, file deleted, rentl.toml points to samples/golden/script.jsonl
- Step 7: PASS — CC0 1.0 Universal license present at samples/golden/LICENSE
- **Overall: PASS**
