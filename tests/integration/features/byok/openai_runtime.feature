Feature: OpenAI-Compatible BYOK Runtime
  As a user with my own API keys
  I want to use OpenAI-compatible endpoints
  So that I can use my preferred LLM provider

  Scenario: Build connection plan from config
    Given a config with multiple BYOK endpoints
    When I build the connection plan
    Then the plan contains validation targets for used endpoints
    And unused endpoints are marked as skipped

  Scenario: Connection validation identifies missing API keys
    Given a config with endpoints requiring API keys
    And some API keys are missing from environment
    When I build the connection plan
    Then endpoints with missing keys are included
