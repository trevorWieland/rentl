# Demo: Documentation Overhaul for v0.1 Release

rentl now has comprehensive documentation for its v0.1 release. In this demo, we'll prove the docs are accurate, complete, and cross-linked — not just that they exist, but that they reflect the actual codebase.

## Environment

- API keys: none needed (documentation verification only)
- External services: none needed
- Setup: none — standard dev environment with uv, Python 3.14, git

## Steps

1. **[RUN]** Verify CHANGELOG completeness — Cross-reference CHANGELOG.md against the roadmap spec list. Every completed v0.1 spec must appear with an accurate description. Expected: all 35+ completed specs are listed.

2. **[RUN]** Verify Getting Started guide commands — Parse `docs/getting-started.md` for code blocks and verify each command is valid (e.g., `uvx rentl --version`, `uvx rentl init`, `uvx rentl doctor`, `uvx rentl run-pipeline`). Run `uvx rentl --help` and confirm all referenced commands exist. Expected: every command in the guide maps to a real CLI command.

3. **[RUN]** Verify architecture doc accuracy — Cross-reference `docs/architecture.md` against the actual codebase: check that listed package names exist under `packages/`, phase names match the pipeline code, and class/type names referenced are real. Verify under 300 lines. Expected: no stale or invented references.

4. **[RUN]** Verify schema reference accuracy — Cross-reference `docs/data-schemas.md` against the actual Pydantic models in `rentl-schemas`. Every documented field must exist in the model, and every model field must be documented. Expected: docs and code are in sync.

5. **[RUN]** Verify license compliance — Check all `pyproject.toml` files for `license = "MIT"`. Verify no copyrighted text files exist in any installable package directory. Confirm benchmark licensing documentation exists. Expected: all license fields present, no bundled copyrighted text.

6. **[RUN]** Verify README cross-links — Check README.md for links to all new docs (getting-started, architecture, data-schemas, CHANGELOG). Expected: all new docs are discoverable from README.

## Results

(Appended by run-demo — do not write this section during shaping)
