# Signposts

- **Task:** Task 2
- **Problem:** The test change validates parsing without `[agents]`, but it does not verify runtime fallback to package defaults, leaving the new `agents=None` branch untested.
- **Evidence:** `tests/unit/cli/test_main.py:367` only executes `config = cli_main._load_resolved_config(config_path)` and `assert config.agents is None`. The new runtime branch is in `packages/rentl-agents/src/rentl_agents/wiring.py:1124`. Coverage on wiring tests reports this branch unexecuted: `Missing ... 1125-1126` from `pytest -q tests/unit/rentl-agents/test_wiring.py --cov=rentl_agents.wiring --cov-report=term-missing --cov-fail-under=0`.
- **Impact:** Future tasks relying on generated configs without `[agents]` can regress at runtime even when schema/CLI parsing tests pass.
