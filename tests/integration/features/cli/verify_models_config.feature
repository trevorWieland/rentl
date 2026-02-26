Feature: Shipped rentl.toml multi-endpoint configuration
  The shipped rentl.toml defines both openrouter and lm-studio endpoints
  so that `rentl verify-models` can resolve endpoint refs for all registry models.

  Scenario: Shipped config loads with both endpoint refs
    Given the shipped rentl.toml config
    When the config is loaded and validated
    Then the config contains an "openrouter" endpoint
    And the config contains a "lm-studio" endpoint
    And the default endpoint is "openrouter"

  Scenario: All registry endpoint refs resolve against shipped config
    Given the shipped rentl.toml config
    And the bundled verified-models registry
    When each registry model's endpoint_ref is looked up
    Then every endpoint_ref maps to a configured endpoint
