# Demo: Install Verification

rentl should be installable and runnable in under a minute by someone who has never seen it before. This demo proves that the uvx installation method works reliably from scratch.

## Steps

1. On a fresh environment (no prior rentl), run `uvx rentl --version` — expected: outputs correct version (e.g., `rentl v0.1.0`)

2. Run `uvx rentl init` in an empty directory — expected: creates project structure (rentl.toml, .env, workspace/), prompts for API key

3. Provide a valid API key when prompted — expected: config is saved, init completes successfully

4. Run `uvx rentl run-pipeline` — expected: pipeline starts and completes without errors

5. Verify the README install instructions match steps 1-4 exactly — expected: commands are copy-pasteable and work verbatim

## Results

### Run 1 — Fresh install verification (2026-02-12 10:10)
- Step 1: PASS — `uvx rentl --version` output "rentl v0.1.7", exit 0
- Step 2: PASS — `uvx rentl init` created rentl.toml, .env, input/, out/, logs/, exit 0
- Step 3: PASS — Valid API key configured in .env, exit 0
- Step 4: PASS — `uvx rentl run-pipeline` completed successfully with status "completed", all 7 phases passed (ingest, context, pretranslation, translate, qa, edit, export), error: null, exit 0
- Step 5: PASS — README commands at lines 21, 49, 77, 95 match demo steps 1-4 exactly and are copy-pasteable
- **Overall: PASS**
