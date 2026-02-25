Feature: End-to-end cost flow in run reports
  Run reports capture cost, waste ratio, and status-segmented token data
  from agent telemetry through to persisted JSON artifacts.

  Scenario: Run report includes cost data from agents with pricing
    Given a workspace with progress data from a mixed-status pipeline with cost
    When I build the run report
    Then the report includes total_cost_usd as a positive number
    And the report includes cost_by_phase with at least one entry
    And the report waste_ratio reflects the failed and retried tokens
    And the report tokens_failed has positive total_tokens
    And the report tokens_retried has positive total_tokens
    And the report is written to disk as valid JSON

  Scenario: Run report gracefully handles agents without cost data
    Given a workspace with progress data from a pipeline without cost
    When I build the run report
    Then the report has null total_cost_usd
    And the report cost_by_phase entries have null cost
    And the report waste_ratio is 0.0
    And the report tokens_failed has zero total_tokens
    And the report tokens_retried has zero total_tokens
    And the report is written to disk as valid JSON

  Scenario: Waste ratio is correct after a mixed-status pipeline run
    Given a workspace with progress data from a mixed-status pipeline with cost
    When I build the run report
    Then the report waste_ratio equals failed plus retried tokens over total tokens
