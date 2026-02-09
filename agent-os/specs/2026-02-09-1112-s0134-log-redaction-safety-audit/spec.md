spec_id: s0.1.34
issue: https://github.com/trevorWieland/rentl/issues/34
version: v0.1

# Spec: Log Redaction & Safety Audit

## Problem

Rentl logs and artifacts can contain resolved secret values (API keys, bearer tokens) in JSONL output. There is no redaction mechanism — the `data` field description in `CommandStartedData.args` says "(redacted)" but nothing enforces it. A leaked log file could expose API credentials.

## Goals

- Automatically redact secret values from all log entries and artifacts before they are persisted or displayed
- Detect hardcoded secrets in config files that should use env var references
- Make redaction transparent — log when it happens, but never log what was redacted

## Non-Goals

- Encrypting log files at rest (out of scope)
- Rotating or managing API keys (operational concern)
- Redacting content within LLM prompts/responses (translation text is not a secret)
- Runtime secret management or vault integration

## Acceptance Criteria

- [ ] A `redact_secrets()` function in `rentl-schemas` scans string values for known secret patterns (API keys, bearer tokens, base64-encoded credentials) and replaces them with `[REDACTED]`
- [ ] `StorageLogSink` and `ConsoleLogSink` apply redaction to the `data` and `message` fields of every `LogEntry` before serialization
- [ ] A `RedactionConfig` Pydantic model defines the secret patterns and env var names to watch; default patterns cover common API key formats (sk-*, Bearer *, key=*, base64 blobs)
- [ ] The redaction system collects actual values of configured `api_key_env` variables at startup and uses those as additional redaction targets
- [ ] Artifact persistence in `rentl-io` applies the same redaction before writing JSONL artifact files
- [ ] `rentl check-secrets` scans `rentl.toml` and `.env` files for hardcoded secrets (values that look like API keys in fields that should be env var references)
- [ ] When redaction occurs, a debug-level log entry records that redaction happened (but not what was redacted)
- [ ] All tests pass including full verification gate
- [ ] Demo passes (see demo.md)

## Note to Code Auditors

Non-negotiables for this spec. Do not approve if any of these are violated:

1. **No secret values in persisted logs** — Resolved API key values (from env vars) must never appear in JSONL log files or console output. The env var *name* (e.g., `RENTL_OPENROUTER_API_KEY`) is fine; the *value* is not.
2. **Redaction at the sink boundary** — Redaction must happen before serialization in the log sink pipeline, not after. Callers must not be responsible for redacting their own data.
3. **No secret values in persisted artifacts** — Artifact JSONL files must also be free of resolved secret values.
4. **Config scanning catches committed secrets** — The `rentl check-secrets` command must detect hardcoded secret values in config files that should use env var references.
