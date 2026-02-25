Feature: Status command cost display
  The status command shows cost summary and waste ratio when cost data is present,
  and gracefully degrades to N/A when cost data is absent.

  Scenario: Status JSON includes cost and waste ratio when agents have cost data
    Given a workspace with progress data containing cost
    When I run status with --json
    Then the command succeeds
    And the JSON response includes total_cost_usd
    And the JSON response includes waste_ratio

  Scenario: Status JSON shows null cost when agents have no cost data
    Given a workspace with progress data without cost
    When I run status with --json
    Then the command succeeds
    And the JSON response has null total_cost_usd
    And the JSON response includes waste_ratio as 0.0

  Scenario: Status display shows cost and waste when cost data is present
    Given a workspace with progress data containing cost
    When I run status without --json
    Then the command succeeds
    And the display output includes a cost row with a dollar amount
    And the display output includes a waste row with a percentage

  Scenario: Status display shows N/A for cost when cost data is absent
    Given a workspace with progress data without cost
    When I run status without --json
    Then the command succeeds
    And the display output includes a cost row showing N/A
    And the display output includes a waste row with a percentage
