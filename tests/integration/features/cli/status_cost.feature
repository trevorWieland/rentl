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
