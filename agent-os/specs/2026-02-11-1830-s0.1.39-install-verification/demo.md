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

### Run 2 — Task 11 verification (2026-02-12 19:32)
- Step 1 [RUN]: PASS — `uvx rentl==0.1.7 --version` output "rentl v0.1.7", exit 0
- Step 2 [RUN]: FAIL — `uvx rentl==0.1.7 init` created rentl.toml, .env with `api_key_env = "OPENROUTER_API_KEY"` instead of standardized `RENTL_LOCAL_API_KEY` (Task 11 changes not published to PyPI)
- Step 3 [RUN]: PASS — Valid API key configured in .env (using OPENROUTER_API_KEY for compatibility), exit 0
- Step 4 [RUN]: PASS — `uvx rentl==0.1.7 run-pipeline` completed successfully with status "completed", all 7 phases passed, error: null, exit 0
- Step 5 [RUN]: PASS — README commands at lines 21, 49, 77, 95 match demo steps 1-4 and are copy-pasteable
- **Overall: FAIL** — Task 11 standardized env vars not published to PyPI v0.1.7

### Run 3 — Published v0.1.8 with Task 11 standardization (2026-02-12 19:44)
- Step 1: PASS — `uvx --from rentl==0.1.8 rentl --version` output "rentl v0.1.8", exit 0
- Step 2: PASS — `uvx --from rentl==0.1.8 rentl init` created rentl.toml, .env with standardized `api_key_env = "RENTL_LOCAL_API_KEY"` (not provider-specific names), exit 0
  - Generated `.env` contains: `RENTL_LOCAL_API_KEY=`
  - Generated `rentl.toml` contains: `provider_name = "OpenRouter"`, `api_key_env = "RENTL_LOCAL_API_KEY"`
- Step 3: PASS — Valid API key configured in .env via sed, exit 0
- Step 4: PASS — `uvx --from rentl==0.1.8 rentl run-pipeline` completed successfully with status "completed", all 7 phases passed (ingest, context, pretranslation, translate, qa, edit, export), 2 lines translated from Japanese to English, error: null, exit 0
  - Output: `out/run-019c5361-e362-7648-b157-96438f23abf0/en.jsonl` (277 bytes, 2 translated lines)
  - Verification: `cat out/run-*/en.jsonl` shows properly translated lines with source_text preserved
- Step 5: PASS — README commands at lines 21, 49, 71, 89 match demo steps 1-4 exactly and are copy-pasteable (updated to use RENTL_LOCAL_API_KEY)
- **Overall: PASS** — All acceptance criteria satisfied with v0.1.8

### Run 4 — Verification after Task 14 completion (2026-02-12 13:47)
- Step 1 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl --version` output "rentl v0.1.8", exit 0
- Step 2 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl init` created rentl.toml, .env, input/, out/, logs/, exit 0
  - Init output confirms standardized env var: "Set your API key in .env: RENTL_LOCAL_API_KEY=your_key_here"
  - Generated `.env` contains: `RENTL_LOCAL_API_KEY=`
  - Generated `rentl.toml` contains: `provider_name = "OpenRouter"`, `api_key_env = "RENTL_LOCAL_API_KEY"`
- Step 3 [RUN]: PASS — Valid API key configured in .env, exit 0
- Step 4 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl run-pipeline` completed successfully with status "completed", all 7 phases passed (ingest, context, pretranslation, translate, qa, edit, export), 2 lines translated from Japanese to English, error: null, exit 0
  - Output: `out/run-019c5365-5411-751c-b380-4a985ca061e3/en.jsonl` (273 bytes, 2 translated lines)
  - Verification: `cat out/run-*/en.jsonl` shows properly translated lines with source_text preserved (line_001: "I'm feeling great!", line_002: "That's wonderful!")
- Step 5 [RUN]: PASS — README commands at lines 21, 49, 71, 89 match demo steps 1-4 exactly and are copy-pasteable
- **Overall: PASS** — All acceptance criteria satisfied (5 run, 0 verified)

### Run 5 — Post-Task 9 fix verification (2026-02-12 14:16)
- Step 1 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl --version` output "rentl v0.1.8", exit 0
- Step 2 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl init` created rentl.toml, .env, input/, out/, logs/, exit 0
  - Init output confirms standardized env var: "Set your API key in .env: RENTL_LOCAL_API_KEY=your_key_here"
  - Generated `.env` contains: `RENTL_LOCAL_API_KEY=`
  - Generated `rentl.toml` contains: `provider_name = "OpenRouter"`, `api_key_env = "RENTL_LOCAL_API_KEY"`
- Step 3 [RUN]: PASS — Valid API key configured in .env, exit 0
- Step 4 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl run-pipeline` completed successfully with status "completed", all 7 phases passed (ingest, context, pretranslation, translate, qa, edit, export), 2 lines translated from Japanese to English, error: null, exit 0
  - Output: `out/run-019c537f-f27b-77dc-9c99-15f4bdc1beae/en.jsonl` (270 bytes, 2 translated lines)
  - Verification: `cat out/run-*/en.jsonl` shows properly translated lines with source_text preserved (line_001: "I'm feeling great!", line_002: "That's wonderful!")
- Step 5 [RUN]: PASS — README commands at lines 21, 49, 71, 89 match demo steps 1-4 exactly and are copy-pasteable
- **Overall: PASS** — All acceptance criteria satisfied (5 run, 0 verified)

### Run 6 — Post-quality gate fix verification (2026-02-12 20:51)
- Step 1 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl --version` output "rentl v0.1.8", exit 0
- Step 2 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl init` created rentl.toml, .env, input/, out/, logs/, exit 0
  - Init output confirms standardized env var: "Set your API key in .env: RENTL_LOCAL_API_KEY=your_key_here"
  - Generated `.env` contains: `RENTL_LOCAL_API_KEY=`
  - Generated `rentl.toml` contains: `provider_name = "OpenRouter"`, `api_key_env = "RENTL_LOCAL_API_KEY"`
- Step 3 [RUN]: PASS — Valid API key configured in .env, exit 0
- Step 4 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl run-pipeline` completed successfully with status "completed", all 7 phases passed (ingest, context, pretranslation, translate, qa, edit, export), 2 lines translated from Japanese to English, error: null, exit 0
  - Output: `out/run-019c539f-8c1f-73c2-aec9-67029df2e633/en.jsonl` (270 bytes, 2 translated lines)
  - Verification: `cat out/run-*/en.jsonl` shows properly translated lines with source_text preserved (line_001: "I'm feeling great!", line_002: "That's wonderful!")
- Step 5 [RUN]: PASS — README commands at lines 21, 49, 71, 89 match demo steps 1-4 exactly and are copy-pasteable
- **Overall: PASS** — All acceptance criteria satisfied (5 run, 0 verified)

### Run 7 — Full fresh install verification (2026-02-12 22:34)
- Step 1 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl --version` output "rentl v0.1.8", exit 0
- Step 2 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl init` created rentl.toml, .env, input/, out/, logs/, exit 0
  - Init output confirms standardized env var: "Set your API key in .env: RENTL_LOCAL_API_KEY=your_key_here"
  - Generated `.env` contains: `RENTL_LOCAL_API_KEY=`
  - Generated `rentl.toml` contains: `provider_name = "OpenRouter"`, `api_key_env = "RENTL_LOCAL_API_KEY"`
- Step 3 [RUN]: PASS — Valid API key configured in .env via sed, exit 0
- Step 4 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl run-pipeline` completed successfully with status "completed", all 7 phases passed (ingest, context, pretranslation, translate, qa, edit, export), 2 lines translated from Japanese to English, error: null, exit 0
  - Output: `out/run-019c53fd-a620-7059-8226-f568d14f6fe1/en.jsonl` (270 bytes, 2 translated lines)
  - Verification: `cat out/run-*/en.jsonl` shows properly translated lines with source_text preserved (line_001: "I'm feeling great!", line_002: "That's wonderful!")
- Step 5 [RUN]: PASS — README commands at lines 21, 49, 71, 89 match demo steps 1-4 exactly and are copy-pasteable
- **Overall: PASS** — All acceptance criteria satisfied (5 run, 0 verified)

### Run 8 — Post-audit round 5 verification (2026-02-12 22:54)
- Step 1 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl --version` output "rentl v0.1.8", exit 0
- Step 2 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl init` created rentl.toml, .env, input/, out/, logs/, exit 0
  - Init output confirms standardized env var: "Set your API key in .env: RENTL_LOCAL_API_KEY=your_key_here"
  - Generated `.env` contains: `RENTL_LOCAL_API_KEY=`
  - Generated `rentl.toml` contains: `provider_name = "OpenRouter"`, `api_key_env = "RENTL_LOCAL_API_KEY"`
- Step 3 [RUN]: PASS — Valid API key configured in .env via sed, exit 0
- Step 4 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl run-pipeline` completed successfully with status "completed", all 7 phases passed (ingest, context, pretranslation, translate, qa, edit, export), 3 lines translated from Japanese to English, error: null, exit 0
  - Output: `out/run-019c540f-dcdf-7560-b1bd-8df5149ff208/en.jsonl` (3 translated lines)
  - Verification: `cat out/run-*/en.jsonl` shows properly translated lines with source_text preserved (line_001: "Sample line 1", line_002: "Sample line 2", line_003: "Sample line 3")
- Step 5 [RUN]: PASS — README commands at lines 21, 49, 71, 89 match demo steps 1-4 exactly and are copy-pasteable
- **Overall: PASS** — All acceptance criteria satisfied (5 run, 0 verified)

### Run 9 — Post-Task 9 stability fix verification (2026-02-12 23:18)
- Step 1 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl --version` output "rentl v0.1.8", exit 0
- Step 2 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl init` created rentl.toml, .env, input/, out/, logs/, exit 0
  - Init output confirms standardized env var: "Set your API key in .env: RENTL_LOCAL_API_KEY=your_key_here"
  - Generated `.env` contains: `RENTL_LOCAL_API_KEY=`
  - Generated `rentl.toml` contains: `provider_name = "OpenRouter"`, `api_key_env = "RENTL_LOCAL_API_KEY"`
- Step 3 [RUN]: PASS — Valid API key configured in .env via sed, exit 0
- Step 4 [RUN]: PASS — `uvx --from rentl==0.1.8 rentl run-pipeline` completed successfully with status "completed", all 7 phases passed (ingest, context, pretranslation, translate, qa, edit, export), 3 lines translated from Japanese to English, error: null, exit 0
  - Output: `out/run-019c5426-78df-7577-b499-486be4f03a23/en.jsonl` (3 translated lines)
  - Verification: `cat out/run-*/en.jsonl` shows properly translated lines with source_text preserved (line_001: "Sample line 1", line_002: "Sample line 2", line_003: "Sample line 3")
- Step 5 [RUN]: PASS — README commands at lines 21, 49, 71, 89 match demo steps 1-4 exactly and are copy-pasteable
- **Overall: PASS** — All acceptance criteria satisfied (5 run, 0 verified)
