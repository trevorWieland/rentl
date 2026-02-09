spec_id: s0.1.34
issue: https://github.com/trevorWieland/rentl/issues/34
version: v0.1

# Plan: Log Redaction & Safety Audit

## Decision Record

Rentl stores API keys as env var references in config (`api_key_env`), but resolved values could leak into JSONL logs and artifacts via the `data` field, error messages, or command args. The redaction system intercepts at the sink boundary — before serialization — so callers don't need to think about it. A separate config scanner catches accidentally hardcoded secrets in config files.

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit on the issue branch and push

- [x] Task 2: Implement redaction core in `rentl-schemas`
  - Create `packages/rentl-schemas/src/rentl_schemas/redaction.py`
    - `SecretPattern` model — compiled regex pattern + human label
    - `RedactionConfig` model — list of patterns, list of env var names to watch
    - `DEFAULT_PATTERNS` — built-in patterns for `sk-*`, `Bearer *`, base64 blobs, etc.
    - `build_redactor(config, env_values)` — returns a `Redactor` with compiled patterns + literal env var values
    - `Redactor.redact(value: str) -> str` — replaces matches with `[REDACTED]`
    - `redact_dict(data: dict) -> dict` — deep-walks a dict, redacting all string values
  - Unit tests in `tests/unit/schemas/test_redaction.py`
    - Pattern matching for each default pattern
    - Literal env var value redaction
    - Deep dict traversal (nested dicts, lists of strings)
    - No false positives on env var *names* (e.g., `RENTL_OPENROUTER_API_KEY` is not redacted)
  - Acceptance: `redact_secrets()` function exists and replaces known patterns with `[REDACTED]`
  - [x] Fix: Make `Redactor.redact_dict` recurse into container values inside lists so all nested strings are redacted (currently `list[dict]` secrets leak). Evidence: `{'items': [{'nested': 'secret123'}, '[REDACTED]']}` from a direct call to `redact_dict`; code path at `packages/rentl-schemas/src/rentl_schemas/redaction.py:117` (audit round 1)
  - [x] Fix: Remove `Any`/`object` typing from redaction core to satisfy `python/strict-typing-enforcement` ("No `Any` or `object` types"). Current violations at `packages/rentl-schemas/src/rentl_schemas/redaction.py:6`, `packages/rentl-schemas/src/rentl_schemas/redaction.py:22`, and `packages/rentl-schemas/src/rentl_schemas/redaction.py:101` (audit round 1)

- [x] Task 3: Wire redaction into log sinks
  - Modify `build_log_sink()` in `packages/rentl-io/src/rentl_io/storage/log_sink.py` to accept a `Redactor`
  - `StorageLogSink` and `ConsoleLogSink` apply `redact_dict` to `entry.data` and `redact` to `entry.message` before writing
  - `CompositeLogSink` passes redactor to child sinks
  - Use composition (wrap sinks with redaction) to avoid changing `LogSinkProtocol`
  - Unit tests in `tests/unit/io/test_log_sink.py` for sink redaction behavior
  - Integration test: write a log entry with a secret, read it back, confirm redacted
  - Acceptance: log sinks redact before write

- [ ] Task 4: Wire redaction into artifact storage
  - Modify `write_artifact_jsonl()` in `packages/rentl-io/src/rentl_io/storage/filesystem.py` to accept/apply redaction
  - Apply `redact_dict` to each record before serialization
  - Unit/integration tests for artifact redaction
  - Acceptance: artifact JSONL files are free of resolved secret values
  - [ ] Fix: Preserve Pydantic JSON-mode serialization in redacted artifact writes. Current code uses `model_dump()` + `json.dumps()` and crashes on JSON-encoded fields such as `UUID` (`TypeError: Object of type UUID is not JSON serializable`) at `packages/rentl-io/src/rentl_io/storage/filesystem.py:644` and `packages/rentl-io/src/rentl_io/storage/filesystem.py:659` (audit round 1)

- [ ] Task 5: Implement `rentl check-secrets` CLI command
  - Add `check-secrets` command to `services/rentl-cli/src/rentl_cli/main.py`
  - Scan `rentl.toml` for `api_key_env` values that look like actual secrets (not env var names)
  - Scan `.env` files for presence (warn if committed / not in .gitignore)
  - Exit 0 for clean, exit 1 for findings
  - Unit tests for scanner logic in `tests/unit/cli/test_check_secrets.py`
  - Acceptance: `rentl check-secrets` catches hardcoded secrets and passes on clean configs

- [ ] Task 6: Bootstrap redactor at startup and pass through CLI
  - In the CLI `run-pipeline` and other commands, build the `Redactor` from config + resolved env vars
  - Pass it to `build_log_sink()` and artifact storage
  - Emit debug-level log when redaction occurs
  - Integration test: end-to-end command with secret in env, verify log output is clean
  - Acceptance: redaction is active by default in all CLI commands; debug log confirms redaction happened
