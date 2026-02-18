---
standard: mandatory-coverage
category: testing
score: 58
importance: High
violations_count: 4
date: 2026-02-17
status: violations-found
---

# Standards Audit: Mandatory Coverage

**Standard:** `testing/mandatory-coverage`
**Date:** 2026-02-17
**Score:** 58/100
**Importance:** High

## Summary

Coverage enforcement exists for unit tests, but it does not align with this standard’s required package scope and is not applied consistently across all test tiers. The TUI feature (`rentl_tui`) has production code with no matching tests in the suite, creating a direct coverage blind spot. Additional low-value tests that assert constants only further reduce behavior-oriented test quality.

## Violations

### Violation 1: Coverage scope does not match mandatory command and misses explicit required modules

- **File:** `Makefile:66-70`
- **Severity:** High
- **Evidence:**
  ```
  unit:
  	$(call run_test, uv run pytest tests/unit -q --tb=short --timeout=1 --cov=packages --cov=services --cov-fail-under=80 --cov-precision=2, .unit.log, Unit Tests)

  test:
  	@uv run pytest --cov=packages --cov=services --cov-report=term-missing
  ```
- **Recommendation:** update CI/unit coverage commands to target the required modules directly, e.g. `--cov=rentl_core --cov=rentl_cli --cov=rentl_tui --cov-fail-under=80` (and match this in any CI workflow).

### Violation 2: Coverage threshold is only enforced on unit suite, not integration/quality tiers

- **File:** `Makefile:71-79`
- **Severity:** High
- **Evidence:**
  ```
  integration:
  	$(call run_test, uv run pytest tests/integration -q --tb=short --timeout=5, .integration.log, Integration Tests)

  quality:
  	$(call run_test, bash -c 'set -a && [ -f .env ] && source .env && set +a && uv run pytest tests/quality -q --tb=short --timeout=90', .quality.log, Quality Tests)
  ```
- **Recommendation:** apply coverage collection and the fail-under threshold to all test tiers (or run a unified PR gate command across unit+integration+quality) so uncovered paths are not hidden behind non-covered suites.

### Violation 3: `rentl_tui` production behavior has no test presence in repo

- **File:** `services/rentl-tui/src/rentl_tui/app.py:9`
- **Severity:** High
- **Evidence:**
  ```
  class RentlApp(App):
      """Rentl TUI application."""
  
      def compose(self) -> ComposeResult:
          yield Header()
          yield Static(f"rentl v{VERSION} - Agentic localization pipeline")
          yield Footer()
  
  def main() -> None:
      app = RentlApp()
      app.run()
  ```
  Verified search in tests found no `rentl_tui`/`textual`/`RentlApp` references:
  ```
  rg --files tests | rg "tui|rentl_tui|textual" && echo "FOUND" || echo "NO_MATCHES"
  NO_MATCHES
  ```
- **Recommendation:** add targeted unit/integration tests for `RentlApp.compose()`, `main()`, and rendering/workflow behavior (or at least smoke tests that import and execute the app path without stubbing all production logic).

### Violation 4: Non-behavioral constant assertion in unit test

- **File:** `tests/unit/core/test_version.py:21-24`
- **Severity:** Low
- **Evidence:**
  ```
  def test_global_version_exists() -> None:
      """Test global VERSION is defined and valid."""
      assert VERSION is not None
      assert str(VERSION) == "0.1.8"
  ```
- **Recommendation:** replace constant-existence assertions with behavior-oriented checks (e.g., parse, format, or compatibility behavior exercised through module consumers).

## Compliant Examples

- `tests/unit/core/test_version.py:7-18` — exercises `VersionInfo` construction and `__str__` behavior directly, which aligns with the standard’s “tests call functions with real inputs” expectation.

## Scoring Rationale

- **Coverage:** The mandatory standard is partially met for many unit tests, but only 3 high-severity enforcement gaps were found (coverage scope, scope of suites, and missing TUI coverage), meaning a significant fraction of required behavior is not validated through this standard. Estimated effective compliance is moderate-to-low.
- **Severity:** Two CI/process violations and one untested feature area are High severity because they can allow regressions to reach CI and release.
- **Trend:** No evidence shows newer coverage policy changes addressing these issues; current workflow remains module-agnostic and TUI remains untested.
- **Risk:** High practical risk of uncovered regressions in TUI and any behavior exercised only in integration/quality flows, with weaker signal quality for at least one constant-only test.
