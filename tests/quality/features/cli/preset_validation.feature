Feature: Provider Preset Validation
  As a rentl developer
  I want to validate provider preset configurations against live APIs
  So that I can catch preset drift before it reaches production

  Scenario: OpenRouter preset validates against live API
    Given the OpenRouter provider preset
    And a fresh project initialized with OpenRouter preset
    When I run doctor with a valid API key
    Then doctor completes successfully
    And the LLM connectivity check passes

  Scenario: All presets have valid structure
    Given the list of endpoint presets
    Then all required presets are present
    And each preset has required fields populated
