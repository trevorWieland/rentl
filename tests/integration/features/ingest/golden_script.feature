Feature: Golden Script Ingest
  As a developer testing the ingest pipeline
  I want to load the golden sample script
  So that I can verify the JSONL adapter works correctly

  Scenario: Ingest golden script through JSONL adapter
    Given the golden script.jsonl file exists
    When I ingest the file through the JSONL adapter
    Then all lines are successfully parsed as SourceLine records
    And line IDs match the expected values
    And text content matches the expected values
    And speakers match the expected values
    And scene IDs match the expected values
