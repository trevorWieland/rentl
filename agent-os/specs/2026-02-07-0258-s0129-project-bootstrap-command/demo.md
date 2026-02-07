# Demo: Project Bootstrap Command

`rentl init` makes starting a new translation project as easy as answering a few questions. Instead of copying example configs and editing TOML by hand, you run one command and get a ready-to-use project that's immediately runnable.

In this demo, we'll prove the init command works end-to-end: from an empty directory to a completed pipeline run.

## Steps

1. Create an empty temp directory and run `rentl init` inside it — walk through the interactive prompts (project name, game name, languages, endpoint, format). Include the seed sample data option. Expected: prompts appear with sensible defaults.

2. After init completes, inspect the created files — expected: `rentl.toml`, `.env`, `input/` directory with seed sample file (3 lines, 1 scene), `out/`, `logs/` all exist.

3. Verify the generated config passes validation — expected: no validation errors.

4. Set the API key env var and run `rentl run-pipeline --config rentl.toml` against the seed data — expected: pipeline completes successfully, producing translated output in `out/`.

5. Run `rentl init` again in the same directory — expected: warns that `rentl.toml` already exists and asks for confirmation.

6. Run `rentl init` in a fresh directory, pressing Enter through all defaults — expected: creates a valid project with all default values, proving the fast-path works.

## Results

### Run 1 — post-task-5 verification (2026-02-07 05:11)
- Step 1: PASS — Interactive prompts work correctly, all defaults accepted
- Step 2: PASS — All expected files created: `rentl.toml`, `.env`, `input/`, `out/`, `logs/`, `input/seed.jsonl` with 3 lines
- Step 3: PASS — Generated config passes `validate_run_config()` schema validation
- Step 4: FAIL — Pipeline execution fails with config error: "Unknown agent 'context' for phase context. Available: basic_editor, direct_translator, idiom_labeler, scene_summarizer, style_guide_critic"
- Step 5: NOT ATTEMPTED — blocked by step 4 failure
- Step 6: NOT ATTEMPTED — blocked by step 4 failure
- **Overall: FAIL**

**Root cause:** Generated TOML uses generic phase names as agent names (e.g., `agents = ["context"]`) instead of actual default agent names (e.g., `agents = ["scene_summarizer"]`). Schema validation passes but runtime agent pool construction fails. See signposts.md for detailed evidence and task 6 in plan.md for fix.
