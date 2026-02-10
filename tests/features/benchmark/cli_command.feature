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
