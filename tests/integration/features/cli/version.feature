Feature: Version Command
  As a user
  I want to check the rentl version
  So that I know which version I'm running

  Scenario: Display version information
    When I run the version command
    Then the command succeeds
    And the output contains the version string
