Feature: Edit Agent Quality
  As a localization team
  I want the edit agent to apply targeted fixes reliably
  So that QA issues are resolved without regressions

  Scenario: Edit agent evaluation passes
    Given an edit agent quality eval dataset
    When I run the edit agent quality evaluation
    Then the edit agent evaluation passes
