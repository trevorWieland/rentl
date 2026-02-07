Feature: Explain Command
  As a user
  I want to understand pipeline phases
  So that I know what each phase does

  Scenario: List all phases
    When I run the explain command with no arguments
    Then the command succeeds
    And the output contains all phase names

  Scenario: Explain a specific phase
    When I run the explain command for phase "translate"
    Then the command succeeds
    And the output contains detailed phase information

  Scenario: Invalid phase name
    When I run the explain command for phase "badphase"
    Then the command fails
    And the output contains valid phase names
