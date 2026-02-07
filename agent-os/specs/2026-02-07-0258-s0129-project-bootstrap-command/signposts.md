# Signposts

- **Task:** Task 2
- **Problem:** The test change validates parsing without `[agents]`, but it does not verify runtime fallback to package defaults, leaving the new `agents=None` branch untested.
- **Evidence:** `tests/unit/cli/test_main.py:367` only executes `config = cli_main._load_resolved_config(config_path)` and `assert config.agents is None`. The new runtime branch is in `packages/rentl-agents/src/rentl_agents/wiring.py:1124`. Coverage on wiring tests reports this branch unexecuted: `Missing ... 1125-1126` from `pytest -q tests/unit/rentl-agents/test_wiring.py --cov=rentl_agents.wiring --cov-report=term-missing --cov-fail-under=0`.
- **Impact:** Future tasks relying on generated configs without `[agents]` can regress at runtime even when schema/CLI parsing tests pass.

- **Task:** Task 3
- **Problem:** `InitAnswers` accepts `input_format="tsv"`, but generated `rentl.toml` cannot validate against `RunConfig`, violating the generated-config contract.
- **Evidence:** `packages/rentl-core/src/rentl_core/init.py:43` types `input_format` as unconstrained `str`, and `packages/rentl-core/src/rentl_core/init.py:226` explicitly treats `"tsv"` as supported seed output. `RunConfig` only allows `FileFormat` values `csv|jsonl|txt` (`packages/rentl-schemas/src/rentl_schemas/primitives.py:84`). Repro output from audit:
  `ValidationError: project.formats.input_format Value error, 'tsv' is not a valid FileFormat` and
  `ValidationError: project.formats.output_format Value error, 'tsv' is not a valid FileFormat`.
- **Impact:** Future CLI work (`rentl init`) can scaffold projects that fail immediately at config validation, creating a broken first-run path.
