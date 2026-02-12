Feature: Golden Script Pipeline Phase Tests
  As a developer testing the pipeline
  I want to verify each pipeline phase works with real LLMs
  So that I can isolate failures to specific phases

  Scenario: Context phase produces scene summaries
    Given a small subset of the golden script
    And a pipeline config with context phase enabled
    When I run the pipeline
    Then the context phase completes successfully

  Scenario: Translate phase produces translated output
    Given a small subset of the golden script
    And a pipeline config with translate and export phases enabled
    When I run the pipeline
    Then the translate phase completes successfully
    And the export output contains valid TranslatedLine records

  Scenario: QA phase completes on translated output
    Given a small subset of the golden script
    And a pipeline config with translate and qa phases enabled
    When I run the pipeline
    Then the qa phase completes successfully

  Scenario: Edit phase completes on translated output
    Given a small subset of the golden script
    And a pipeline config with translate and edit phases enabled
    When I run the pipeline
    Then the edit phase completes successfully
