# References: Functional Onboarding

## Implementation Files

### Core Logic
- `packages/rentl-core/src/rentl_core/init.py` — Project generation (`generate_project()`, `InitAnswers`, `InitResult`)
- `packages/rentl-core/src/rentl_core/doctor.py` — Diagnostic checks (`run_doctor()`, `check_api_keys()`, `check_llm_connectivity()`)
- `packages/rentl-core/src/rentl_core/help.py` — Command help (`get_command_help()`, `list_commands()`)
- `packages/rentl-core/src/rentl_core/explain.py` — Phase explanation (`get_phase_info()`, `list_phases()`)

### CLI Surface
- `services/rentl-cli/src/rentl_cli/main.py` — All CLI commands (init, doctor, run-pipeline, export, help, explain)
  - `doctor()` — Lines ~335-420 (missing `_load_dotenv` call)
  - `init()` — Lines ~518-633 (provider prompts at ~561-563)
  - `_render_run_execution_summary()` — Lines ~2383-2448 (missing next steps)
  - `_load_dotenv()` — Line ~2100 (existing dotenv loader used by other commands)

### Tests
- `tests/unit/core/test_init.py` — Init unit tests (56 tests)
- `tests/unit/core/test_doctor.py` — Doctor unit tests (50+ tests)
- `tests/integration/cli/test_init.py` — Init integration tests (BDD)
- `tests/integration/cli/test_doctor.py` — Doctor integration tests (BDD)

## Issues
- #23 — s0.1.22 Functional Onboarding (this spec)
- s0.1.30 — Onboarding Docs Pack (depends on this spec, deferred)

## Dependencies (All Complete)
- s0.1.11 — CLI Workflow & Phase Selection
- s0.1.13 — BYOK Runtime Integration
- s0.1.15 — Initial Phase Agent: Context
- s0.1.16 — Initial Phase Agent: Pretranslation
- s0.1.17 — Initial Phase Agent: Translate
- s0.1.18 — Initial QA Checks (Deterministic)
- s0.1.19 — Initial Phase Agent: QA
- s0.1.20 — Initial Phase Agent: Edit
- s0.1.29 — Project Bootstrap Command
- s0.1.31 — CLI Help/Doctor Commands
