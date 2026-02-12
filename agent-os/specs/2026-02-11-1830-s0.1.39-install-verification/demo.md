# Demo: Install Verification

rentl should be installable and runnable in under a minute by someone who has never seen it before. This demo proves that the uvx installation method works reliably from scratch.

## Steps

1. On a fresh environment (no prior rentl), run `uvx rentl --version` — expected: outputs correct version (e.g., `rentl v0.1.0`)

2. Run `uvx rentl init` in an empty directory — expected: creates project structure (rentl.toml, .env, workspace/), prompts for API key

3. Provide a valid API key when prompted — expected: config is saved, init completes successfully

4. Run `uvx rentl run-pipeline` — expected: pipeline starts and completes without errors

5. Verify the README install instructions match steps 1-4 exactly — expected: commands are copy-pasteable and work verbatim

## Results

(Appended by run-demo — do not write this section during shaping)
