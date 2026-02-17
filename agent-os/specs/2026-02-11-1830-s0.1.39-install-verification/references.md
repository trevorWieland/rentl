# References: Install Verification

## Implementation Files

- `services/rentl-cli/pyproject.toml` — Package configuration (rename to `name = "rentl"`)
- `services/rentl-cli/src/rentl_cli/main.py` — CLI implementation (init, run-pipeline, etc.)
- `pyproject.toml` — Workspace root configuration (update workspace source and dev deps)
- `README.md` — Install instructions to update

## Related Issues

- Issue #39 — s0.1.39 Install Verification (uvx/uv tool)

## Dependencies

- s0.1.29 — (check issue for details)
- s0.1.24 — (check issue for details)

## External Resources

- [uv publish guide](https://docs.astral.sh/uv/guides/package/) — How to build and publish with uv
- [PyPI](https://pypi.org/project/rentl/) — Package registry target (after publish)
