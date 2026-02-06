# Demo: CLI Exit Codes + Error Taxonomy

The CLI now returns stable, distinct exit codes that CI pipelines and scripts can branch on. Previously, every failure returned exit code 1. Now, a config error returns a different code than a validation error or a runtime crash — so your `if` statements and monitoring can tell the difference.

## Steps

1. **Success case** — Run `rentl version` and confirm exit code 0.
   Expected: exit code is 0, command prints version info.

2. **Config error** — Run `rentl run-pipeline` with a malformed config file and confirm the exit code matches the config error code from the `ExitCode` enum (not generic 1).
   Expected: exit code is 10 (CONFIG_ERROR), stderr shows a config-related error message.

3. **Validation error** — Run `rentl export` with invalid arguments and confirm the exit code matches the validation error code.
   Expected: exit code is 11 (VALIDATION_ERROR), stderr shows a validation-related error message.

4. **JSON mode exit codes** — Re-run step 2 with `--output json` and confirm (a) the same non-zero exit code is returned, and (b) the JSON envelope includes the exit code integer and error code string.
   Expected: exit code is 10, JSON output contains `"exit_code": 10` in the error section.

5. **Scripting proof** — Run a short shell snippet that branches on exit code:
   ```bash
   rentl run-pipeline --config bad.yml 2>/dev/null; code=$?
   case $code in
     0)  echo "Success" ;;
     10) echo "Config error — check your config file" ;;
     11) echo "Validation error — check your inputs" ;;
     *)  echo "Other error (exit code: $code)" ;;
   esac
   ```
   Expected: the script prints "Config error — check your config file" and the exit code is 10.

## Results

### Run 1 — Full demo validation (2026-02-06 23:50)
- Step 1: PASS — `rentl version` returned exit code 0 and printed version info "rentl v0.1.0"
- Step 2: PASS — `rentl run-pipeline --config bad.yml` returned exit code 10 (CONFIG_ERROR) with JSON error: "Failed to read config: Expected '=' after a key in a key/value pair"
- Step 3: PASS — `rentl export --input /tmp/nonexistent.parquet --format csv --output /tmp/test_export.csv` returned exit code 11 (VALIDATION_ERROR) with JSON error: "Failed to read input: [Errno 2] No such file or directory"
- Step 4: PASS — `rentl run-pipeline --config bad.yml` returned exit code 10, JSON output contains `"exit_code": 10` in error section (Note: CLI returns JSON by default for errors; no `--output json` flag needed)
- Step 5: PASS — Shell script correctly branched on exit code 10 and printed "Config error — check your config file"
- **Overall: PASS**
