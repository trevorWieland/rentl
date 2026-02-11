# Stale Reference Prevention

Cross-reference audits must verify against actual CLI output and config files — never assume.

**Principle:** Code is truth. Grep actual output, not memory.

```bash
# Verify README command table matches CLI
uv run rentl --help | grep -E "^  rentl" | sort

# Verify config keys are documented
grep -E "^\[|^]" rentl.toml.example | head -20

# Verify env vars match .env.example
cat .env.example | grep -v "^#" | grep -v "^$"
```

Common stale reference patterns:
- Env var names hardcoded in docs (use `api_key_env` pattern)
- CLI option values that no longer exist (check `--help` output)
- File paths that assume a specific run ID
