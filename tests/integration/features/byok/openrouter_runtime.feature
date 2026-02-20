Feature: OpenRouter Provider Parity
  As a user with an OpenRouter API key
  I want requests to route correctly based on base URL
  So that provider-specific features work transparently

  Scenario: OpenRouter base URL selects OpenRouter provider
    Given an OpenRouter endpoint configuration
    When I send a prompt through the runtime
    Then the request is sent to the OpenRouter endpoint
    And the response contains the expected output

  Scenario: Non-OpenRouter URL uses OpenAI provider
    Given a local endpoint configuration
    When I send a prompt through the runtime
    Then the request is sent to the local endpoint
    And the response contains the expected output

  Scenario: Provider switching requires config only
    Given multiple endpoint configurations for different providers
    When I send prompts through each endpoint
    Then each request reaches the correct endpoint
    And each response contains the correct model ID
