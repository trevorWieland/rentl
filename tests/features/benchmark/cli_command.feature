Feature: Benchmark CLI Command
  As a rentl user
  I want to run benchmark evaluations via CLI
  So that I can compare rentl translations against MTL baseline

  Scenario: Run benchmark with demo slice (mocked LLMs)
    Given a valid rentl configuration exists
    And a benchmark eval set is available
    And LLM endpoints are mocked
    When I run benchmark command with demo slice
    Then the command succeeds
    And the output includes download progress
    And the output includes MTL baseline generation
    And the output includes judging progress
    And the output includes benchmark report summary
    And dimension aggregates are displayed

  Scenario: Run benchmark with JSON output
    Given a valid rentl configuration exists
    And a benchmark eval set is available
    And LLM endpoints are mocked
    And output path is specified
    When I run benchmark command with JSON output
    Then the command succeeds
    And a JSON report file is created
    And the report contains per-line scores
    And the report contains dimension aggregates
    And the report contains head-to-head comparison

  Scenario: Fail when API key missing
    Given a valid rentl configuration exists
    And OPENAI_API_KEY is not set
    When I run benchmark command
    Then the command fails
    And error message indicates missing API key

  Scenario: Fail when slice not found
    Given a valid rentl configuration exists
    And LLM endpoints are mocked
    When I run benchmark command with invalid slice
    Then the command fails
    And error message lists available slices
