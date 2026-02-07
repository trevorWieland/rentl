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

(Appended by run-demo — do not write this section during shaping)
