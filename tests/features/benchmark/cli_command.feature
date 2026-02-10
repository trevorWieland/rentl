Feature: Benchmark CLI Command
  As a rentl user
  I want to run benchmark evaluations via CLI
  So that I can compare rentl translations against baselines

  Note: Task 7 is complete. The benchmark command now has working download and compare subcommands.

  Scenario: Benchmark command requires a subcommand
    Given a valid rentl configuration exists
    When I run benchmark command
    Then the command exits with status 2
    And the output indicates a subcommand is required

  Scenario: Benchmark download accepts kebab-case eval-set names
    Given a valid rentl configuration exists
    When I run benchmark download with kebab-case eval-set name
    Then the command normalizes to snake_case internally
    And the download succeeds
