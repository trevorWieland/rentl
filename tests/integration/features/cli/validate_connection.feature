Feature: Validate Connection Command
  As a user with configured BYOK endpoints
  I want to validate my LLM connections
  So that I know my configuration is correct before running pipelines

  Scenario: Validate connection with all endpoints configured
    Given a rentl config with multiple endpoints
    And all required API keys are set in environment
    When I run the validate-connection command
    Then the command succeeds
    And the response shows successful validations
    And the response shows skipped endpoints

  Scenario: Validate connection with missing config
    Given no config file exists
    When I run the validate-connection command with the missing config
    Then the command succeeds with an error response
    And the error code is "config_error"
