Feature: Benchmark Quality Validation
  As a rentl developer
  I want to validate benchmark comparison mechanics with real LLMs
  So that I can ensure judge head-to-head comparison returns per-line results with reasoning

  Scenario: Compare translation outputs with real LLM judge
    Given sample translation output files exist
    And real LLM endpoints are configured
    When I run benchmark compare on the output files
    Then the benchmark completes successfully
    And per-line head-to-head results are present
    And each result includes judge reasoning
    And all rubric dimensions have winners
    And pairwise summaries include win rates
    And Elo ratings are computed
