# Demo: Codebase Modernization & CI Enforcement

Codebase Modernization & CI Enforcement brings the repo to full compliance with 9 standards: migrating all dataclasses to Pydantic, converting legacy dispatches to match/case, enabling strict typing, enforcing the `make all` gate in CI, and cleaning up deprecations, type gaps, and placeholder artifacts. This is a code health spec — the demo proves everything compiles, passes, and is enforceable.

## Environment

- API keys: None required (no LLM calls in this spec)
- External services: None
- Setup: `make all` must be runnable (local tooling: uv, ruff, ty, pytest)

## Steps

1. **[RUN]** Verify zero dataclasses remain — `grep -r '@dataclass' packages/ services/ scripts/ tests/` returns no matches
2. **[RUN]** Verify no legacy if/elif phase dispatches — spot-check converted match/case blocks in orchestrator.py, wiring.py, main.py
3. **[RUN]** Run `ty check` in strict mode — expected: clean exit, no errors
4. **[RUN]** Run `make all` — expected: all gates pass (format, lint, type, unit, integration, quality)
5. **[RUN]** Verify CI workflow exists and is correctly configured — check `.github/workflows/ci.yml` for `make all` trigger on PRs
6. **[RUN]** Run pytest with `-W error::DeprecationWarning` — expected: no deprecation warnings surface as errors
7. **[RUN]** Verify `ApiResponse` envelope on health endpoint — inspect the endpoint code for correct wrapping
8. **[RUN]** Verify dependency version specs use compatible ranges — check pyproject.toml files for upper bounds

## Results

(Appended by run-demo — do not write this section during shaping)
