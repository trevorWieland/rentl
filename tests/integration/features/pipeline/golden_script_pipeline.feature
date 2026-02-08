Feature: Golden Script Full Pipeline
  As a developer testing the full pipeline
  I want to run all phases on the golden sample script
  So that I can verify the end-to-end pipeline works correctly

  Scenario: Run full pipeline on golden script with fake LLM
    Given the golden script exists at samples/golden/script.jsonl
    And a pipeline config with all phases enabled
    And the FakeLlmRuntime is configured
    When I run the full pipeline on the golden script
    Then all phases complete successfully
    And the export output contains valid TranslatedLine records
