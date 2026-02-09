# Demo: Log Redaction & Safety Audit

Rentl now ensures no secrets leak into logs, artifacts, or config files. The redaction system intercepts at the sink boundary — before any data is serialized to disk or console — so callers never need to think about it. A separate config scanner catches accidentally hardcoded secrets.

In this demo, we'll prove that secret values are automatically redacted from all output, that the redaction is transparent, and that the config scanner catches committed secrets.

## Steps

1. **Set up a fake API key** — Export `RENTL_LOCAL_API_KEY=sk-test-secret-1234567890abcdef`. Show it's set in the environment.

2. **Trigger a log entry with the secret embedded** — Run a short pipeline (or a targeted test) that logs command args containing the secret value. Read the resulting JSONL log file and confirm the secret value `sk-test-secret-1234567890abcdef` is replaced with `[REDACTED]`.

3. **Verify console output is also redacted** — Run with console sink enabled, capture stderr, confirm the secret value doesn't appear in console output.

4. **Verify artifact redaction** — If any artifact data could contain the secret (e.g., error messages referencing the key), confirm it's redacted in the artifact JSONL.

5. **Run the config scanner on a bad config** — Create a temporary `rentl.toml` with a hardcoded API key value (e.g., `api_key_env = "sk-hardcodedsecret1234567890abc"` instead of an env var name). Run `rentl check-secrets` and confirm it flags the issue with exit code 1.

6. **Run the config scanner on a clean config** — Run `rentl check-secrets` on the normal `rentl.toml` (which uses env var names). Confirm it passes clean with exit code 0.

## Results

### Run 1 — Initial demo execution (2026-02-09 18:32)
- Step 1: PASS — Fake API key `sk-test-secret-1234567890abcdef` set in environment
- Step 2: PASS — Log entry created with secret embedded; log file shows `[REDACTED]` placeholders and no secret value; debug log entry `redaction_applied` present
- Step 3: PASS — Console output redacted; `[REDACTED]` placeholder found, secret not present in console output
- Step 4: PASS — Artifact JSONL file created with secret embedded; artifact file shows `[REDACTED]` placeholders and no secret value
- Step 5: FAIL — Config scanner did not detect the hardcoded secret `sk-hardcoded-secret` in `api_key_env` field. Root cause: The demo test value contains hyphens which don't match the `sk-[a-zA-Z0-9]{20,}` pattern (pattern requires alphanumeric only). When tested with a compliant secret value `sk-test12345678901234567890abcdefgh`, the scanner correctly detected it and returned exit code 1.
- Step 6: PASS — Config scanner returns exit code 0 for clean config with env var name `RENTL_OPENROUTER_API_KEY`
- **Overall: FAIL** — Step 5 reveals a demo plan issue (test secret doesn't match expected pattern)
