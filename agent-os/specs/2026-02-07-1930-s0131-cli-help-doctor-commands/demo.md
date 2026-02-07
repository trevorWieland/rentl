# Demo: CLI Help/Doctor Commands

rentl now has built-in diagnostics so users can understand what's available, troubleshoot setup issues, and learn about each pipeline phase — all without leaving the terminal. In this demo, we'll prove all three commands work correctly and provide genuinely useful output.

## Steps

1. **`rentl help`** — Run with no arguments. Expected: a formatted summary of all commands (init, run-pipeline, run-phase, status, export, validate-connection, help, doctor, explain) with brief descriptions.

2. **`rentl help doctor`** — Run help for a specific command. Expected: detailed help showing doctor's purpose, options, and examples.

3. **`rentl doctor` (no project)** — Run doctor outside a rentl project directory (e.g., from `/tmp`). Expected: graceful handling — reports missing config as a failure with a fix suggestion (e.g., "run `rentl init`"), does not crash.

4. **`rentl doctor` (valid project)** — Run doctor inside an initialized project. Expected: all checks run and display a pass/fail/warn summary table. Config, workspace, and Python version checks pass. API key / connectivity checks show warn or fail with actionable suggestions.

5. **`rentl explain`** — Run with no phase argument. Expected: lists all 7 phases with one-line descriptions.

6. **`rentl explain translate`** — Run for a specific phase. Expected: displays what the translate phase does, its inputs (pretranslation output), outputs (translated lines), prerequisites (context + pretranslation), and relevant config options.

7. **`rentl explain badphase`** — Run with an invalid phase name. Expected: helpful error listing all valid phase names.

## Results

(Appended by run-demo — do not write this section during shaping)
