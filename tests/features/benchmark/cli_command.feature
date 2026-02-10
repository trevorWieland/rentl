Feature: Benchmark CLI Command (Stub - Task 7 Pending)
  As a rentl user
  I want to run benchmark evaluations via CLI
  So that I can compare rentl translations against MTL baseline

  Note: The benchmark command is currently stubbed out during Task 4-6 refactor.
  Task 7 will implement the full `rentl benchmark download` and `rentl benchmark compare` subcommands.

  Scenario: Benchmark command displays rewrite notice
    Given a valid rentl configuration exists
    When I run benchmark command
    Then the command exits with status 1
    And the output indicates command is being rewritten
