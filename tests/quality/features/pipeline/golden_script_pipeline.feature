Feature: Golden Script Pipeline Per-Phase Tests
  As a developer testing the pipeline
  I want to verify the pipeline works end-to-end with real LLMs
  So that I can catch integration issues between phases

  Scenario: Translate phase produces translated output
    Given a small subset of the golden script
    And a pipeline config with translate and export phases enabled
    When I run the pipeline
    Then the pipeline completes successfully
    And the export output contains valid TranslatedLine records
