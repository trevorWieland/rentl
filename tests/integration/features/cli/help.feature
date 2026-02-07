Feature: Help Command
  As a user
  I want to view help for CLI commands
  So that I can understand how to use rentl

  Scenario: List all commands
    When I run the help command with no arguments
    Then the command succeeds
    And the output contains command names

  Scenario: Show help for a specific command
    When I run the help command for "version"
    Then the command succeeds
    And the output contains detailed help for version

  Scenario: Invalid command name
    When I run the help command for "nonexistent"
    Then the command fails
    And the output contains an error message
