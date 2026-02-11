Feature: Doctor Command
  As a user
  I want to run diagnostics on my rentl setup
  So that I can identify and fix configuration issues

  Scenario: Run doctor with valid config
    Given a valid rentl configuration exists
    When I run the doctor command
    Then the command succeeds
    And the output contains check results

  Scenario: Run doctor without config file
    Given no rentl configuration exists
    When I run the doctor command
    Then the command fails
    And the output contains config error details

  Scenario: Run doctor outside project directory
    Given no rentl configuration exists
    When I run the doctor command
    Then the command fails
    And the output contains config error details
    And the output contains actionable fix suggestions

  Scenario: Doctor loads API keys from .env file
    Given a valid rentl configuration exists
    And API keys are set in .env file
    When I run the doctor command
    Then the command succeeds
    And the API key check passes
