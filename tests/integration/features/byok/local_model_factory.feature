Feature: Local Model Factory Pipeline
  As a developer using local LLM endpoints
  I want the model factory to route local URLs correctly
  So that local models work through the agent pipeline

  Scenario: Factory routes local URL to OpenAI model
    Given a local model endpoint
    When I create a model through the factory
    Then the model is an OpenAIChatModel instance
    And the temperature setting is preserved

  Scenario: Factory to agent plain text output
    Given a local model endpoint with mocked HTTP
    When I run an agent with plain text output
    Then the agent returns the mocked text response
    And the HTTP endpoint was called

  Scenario: Factory to agent structured output
    Given a local model endpoint with mocked tool call HTTP
    When I run an agent with structured output
    Then the agent returns the structured response
    And the HTTP endpoint was called

  Scenario: Runtime with local model
    Given a local model endpoint with mocked HTTP
    When I run a prompt through the OpenAI-compatible runtime
    Then the runtime returns the expected response
    And the HTTP endpoint was called
