Feature: End-to-End Onboarding
  As a new user
  I want to complete the full onboarding flow
  So that I can translate content without manual config edits

  Scenario: Full onboarding flow succeeds
    Given a clean temporary directory
    When I run init with preset provider selection
    And I run doctor in the project directory
    And I run the pipeline with the generated config
    And I run export for the pipeline output
    Then all commands succeed
    And the export produces output files
    And no manual edits were required
