Feature: Retry Recovery Quality
  As a localization team
  I want required-tool recovery to work with a real LLM
  So that agents reliably call required tools before producing output

  Scenario: Recovery enforcement with real LLM
    Given a retry recovery quality eval dataset
    When I run the retry recovery quality evaluation
    Then the retry recovery evaluation passes
