Feature: Model Compatibility Verification
  As a localization team
  I want to verify that each registered model works through the full pipeline
  So that I can trust models in the verified registry

  Scenario: Verified model passes all pipeline phases
    Given a verified model entry and its endpoint configuration
    When I run compatibility verification against the model
    Then all five pipeline phases pass
    And the verification result reports overall success
