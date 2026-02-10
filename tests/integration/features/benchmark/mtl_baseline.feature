Feature: MTL Baseline Translation
  As a benchmark harness
  I want to generate minimal translation baselines
  So that I can fairly compare rentl against raw machine translation

  Scenario: MTL baseline flow validates minimal prompt structure
    Given a set of source lines for translation
    And a mocked LLM runtime
    When I generate MTL baseline translations
    Then all prompts use minimal translation structure
    And no prompts include context injection
    And all results are valid TranslatedLine objects
    And all results are marked as MTL baseline

  Scenario: MTL baseline respects concurrency limits
    Given a large set of source lines
    And a mocked LLM runtime that tracks concurrency
    And a concurrency limit of 2
    When I generate MTL baseline translations
    Then concurrent calls never exceed the limit
    And all translations complete successfully
