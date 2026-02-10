Feature: Benchmark Quality Validation
  As a rentl developer
  I want to validate benchmark mechanics with real LLMs
  So that I can ensure judge scoring returns proper per-line scores with reasoning

  Scenario: Run benchmark on demo slice with real LLMs
    Given a valid rentl configuration exists
    And the demo slice is configured
    And real LLM endpoints are configured
    When I run benchmark on the demo slice
    Then the benchmark completes successfully
    And per-line scores are present for all evaluated lines
    And each score includes judge reasoning
    And all rubric dimensions have scores
    And dimension aggregates are computed
    And head-to-head results include winner selections
