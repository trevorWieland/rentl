# Demo: Log Redaction & Safety Audit

Rentl now ensures no secrets leak into logs, artifacts, or config files. The redaction system intercepts at the sink boundary — before any data is serialized to disk or console — so callers never need to think about it. A separate config scanner catches accidentally hardcoded secrets.

In this demo, we'll prove that secret values are automatically redacted from all output, that the redaction is transparent, and that the config scanner catches committed secrets.

## Steps

1. **Set up a fake API key** — Export `RENTL_LOCAL_API_KEY=sk-test-secret-1234567890abcdef`. Show it's set in the environment.

2. **Trigger a log entry with the secret embedded** — Run a short pipeline (or a targeted test) that logs command args containing the secret value. Read the resulting JSONL log file and confirm the secret value `sk-test-secret-1234567890abcdef` is replaced with `[REDACTED]`.

3. **Verify console output is also redacted** — Run with console sink enabled, capture stderr, confirm the secret value doesn't appear in console output.

4. **Verify artifact redaction** — If any artifact data could contain the secret (e.g., error messages referencing the key), confirm it's redacted in the artifact JSONL.

5. **Run the config scanner on a bad config** — Create a temporary `rentl.toml` with a hardcoded API key value (e.g., `api_key_env = "sk-hardcoded-secret"` instead of an env var name). Run `rentl check-secrets` and confirm it flags the issue with exit code 1.

6. **Run the config scanner on a clean config** — Run `rentl check-secrets` on the normal `rentl.toml` (which uses env var names). Confirm it passes clean with exit code 0.

## Results

(Appended by run-demo — do not write this section during shaping)
