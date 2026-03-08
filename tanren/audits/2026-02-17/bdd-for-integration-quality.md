---
standard: bdd-for-integration-quality
category: testing
score: 79
importance: High
violations_count: 6
date: 2026-02-17
status: violations-found
---

# Standards Audit: BDD for Integration & Quality Tests

**Standard:** `testing/bdd-for-integration-quality`
**Date:** 2026-02-17
**Score:** 79/100
**Importance:** High

## Summary

Integration and quality suites are largely aligned to the BDD standard, but there are legacy-style integration/quality tests that still use direct `test_*` functions with inline assertions and no `Given/When/Then` step structure. Most of the codebase appears to follow scenario-driven tests, so impact is localized but meaningful: 6 files still bypass the standard and create inconsistent test patterns across suites. Coverage has improved in newer feature-driven tests, but these exceptions show incomplete migration.

## Violations

### Violation 1: Integration/quality test modules use direct assertions without BDD step fixtures

- **File:** `tests/integration/core/test_deterministic_qa.py:29`
- **Severity:** Medium
- **Evidence:**
  ```python
  def test_given_lines_with_issues_when_running_qa_then_issues_detected(
      self,
  ) -> None:
      ...
      # When: Running checks
      issues = runner.run_checks(lines)

      # Then: Issues detected for problematic lines
      line_ids_with_issues = {issue.line_id for issue in issues}
      assert "line_1" not in line_ids_with_issues
  ```
- **Recommendation:** Convert these class methods into BDD-scoped step definitions (`@given`, `@when`, `@then`) and bind them via feature scenarios. Example pattern:
  ```python
  @scenario("features/qa/deterministic_qa.feature", "Detects deterministic QA issues")
  def test_deterministic_qa_detects_issues():
      pass

  @given("a set of translated lines with known issues", target_fixture="ctx")
  def given_sample_qa_lines():
      ...
  ```

### Violation 2: Integration auto-migration test file uses direct `test_*` assertions instead of scenario flow

- **File:** `tests/integration/core/test_doctor.py:21`
- **Severity:** Medium
- **Evidence:**
  ```python
  def test_given_outdated_config_when_checking_validity_then_auto_migrates(
      self, tmp_path: Path
  ) -> None:
      ...
      result = check_config_valid(config_path)

      # Then: Check passes
      assert result.status == CheckStatus.PASS
      assert result.fix_suggestion is None
  ```
- **Recommendation:** Move this behavior into BDD scenarios that bind config fixtures to the action (`@when I run check_config_valid`) and assertions to `@then` steps for migration outcome and backup checks.

### Violation 3: Integration BYOK runtime parity test file is outside BDD style

- **File:** `tests/integration/byok/test_openrouter_runtime.py:23`
- **Severity:** Medium
- **Evidence:**
  ```python
  def test_openrouter_base_url_selects_openrouter_provider(self) -> None:
      runtime = OpenAICompatibleRuntime()
      ...
      asyncio.run(runtime.run_prompt(request, api_key="test-key"))
      assert mock_provider.called
      assert mock_model.called
  ```
- **Recommendation:** Refactor these provider-selection checks into BDD steps with explicit `Given a request with ...`, `When runtime executes ...`, `Then OpenRouterProvider is selected` semantics.

### Violation 4: Integration filesystem redaction tests define direct test functions outside BDD scenarios

- **File:** `tests/integration/storage/test_filesystem.py:298`
- **Severity:** Medium
- **Evidence:**
  ```python
  def test_log_sink_redacts_secrets_end_to_end(tmp_path: Path) -> None:
      ...
      sink = build_log_sink(logging_config, log_store, redactor=redactor)
      asyncio.run(sink.emit_log(entry))
      log_lines = log_path.read_text(...)
      assert "[REDACTED]" in redacted_entry["message"]
  ```
- **Recommendation:** Keep these assertions but place them in `@then` steps under scenario(s) so behavior is documented in one Given/When/Then flow with shared context.

### Violation 5: Quality preset validation test uses direct integration-style assertions, not BDD scenario flow

- **File:** `tests/quality/cli/test_preset_validation.py:30`
- **Severity:** Medium
- **Evidence:**
  ```python
  @pytest.mark.quality
  @pytest.mark.api
  def test_openrouter_preset_validates_against_live_api(
      tmp_path: Path,
      cli_runner: CliRunner,
      monkeypatch: pytest.MonkeyPatch,
  ) -> None:
      ...
      init_result = cli_runner.invoke(...)
      assert init_result.exit_code == 0
  ```
- **Recommendation:** Convert to feature-backed BDD (`scenarios(...)` + Given/When/Then steps) while keeping quality-specific marks in either tags or runtime metadata.

### Violation 6: Integration init regression tests bypass BDD style for additional integration checks

- **File:** `tests/integration/cli/test_init.py:465`
- **Severity:** Medium
- **Evidence:**
  ```python
  def test_env_var_scoping_regression(
      tmp_path: Path, monkeypatch: pytest.MonkeyPatch
  ) -> None:
      ...
      with monkeypatch.context() as m:
          m.setenv(StandardEnvVar.API_KEY.value, "fake-api-key-for-scoping-test")
          assert os.environ.get(StandardEnvVar.API_KEY.value) == "fake-api-key-for-scoping-test"
      assert os.environ.get(StandardEnvVar.API_KEY.value) == original_value
  ```
- **Recommendation:** Merge these regression checks into BDD scenarios so they align with surrounding init behavior tests in the same module.

## Compliant Examples

- `tests/integration/byok/test_openai_runtime.py:22` — Uses `scenarios(...)` with `@given/@when/@then` step definitions.
- `tests/quality/benchmark/test_benchmark_quality.py:34` — Scenario-linked quality tests with context/steps and explicit Given/When/Then fixtures.
- `tests/integration/storage/test_protocol.py:55` — BDD storage protocol coverage using feature-driven `scenarios` and step decorators.

## Scoring Rationale

- **Coverage:** 34 integration/quality test files were examined; 28 are currently BDD-first (`28/34 = ~82%`). The remaining 6 files still contain direct `test_*` functions.
- **Severity:** Violations are mostly `Medium`; there are no Critical or High functional failures identified, but these files are inconsistent with the adopted integration/quality testing convention.
- **Trend:** Newer/feature-centric suites are consistently BDD-formatted, while older modules (`core/*` integration and some BYOK/storage/quality helpers) still need migration.
- **Risk:** Medium operational risk for long-term maintainability and onboarding: test intent is less discoverable, and behavior documentation is inconsistent across integration/quality domains.
