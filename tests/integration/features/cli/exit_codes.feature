Feature: CLI Exit Codes
  As a CI/CD pipeline or script user
  I want the CLI to return distinct exit codes for different failure categories
  So that I can branch on failure types and handle them appropriately

  Scenario: Success returns exit code 0
    When I run the version command
    Then the command succeeds

  Scenario: Config error returns exit code 10
    Given no config file exists
    When I run run-pipeline with the missing config
    Then the command returns an error response
    And the exit code is 10
    And the error code is "config_error"

  Scenario: Validation error returns exit code 11
    Given a rentl config with valid settings
    When I run export with an invalid run ID
    Then the command returns an error response
    And the exit code is 11
    And the error code is "validation_error"

  Scenario: Runtime error returns exit code 99
    Given a rentl config with valid settings
    When I trigger a runtime error in the CLI
    Then the command returns an error response
    And the exit code is 99
    And the error code is "runtime_error"

  Scenario: JSON mode preserves exit codes
    Given no config file exists
    When I run run-pipeline with the missing config in JSON mode
    Then the command returns an error response
    And the exit code is 10
    And the JSON response includes exit_code field with value 10
