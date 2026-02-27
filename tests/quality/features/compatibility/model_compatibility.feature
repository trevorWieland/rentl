Feature: Model Compatibility Verification
  As a localization team
  I want to verify that each registered model works through the full pipeline
  So that I can trust models in the verified registry

  Scenario: Verified model passes a single pipeline phase
    Given a verified model entry and its endpoint configuration
    When I run single-phase compatibility verification against the model
    Then the pipeline phase passes
