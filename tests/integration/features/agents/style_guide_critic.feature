Feature: Style Guide Critic Profile Loading
  As a developer
  I want to load style guide critic profiles from TOML files
  So that QA agents can be configured declaratively

  Scenario: Load style guide critic profile
    Given a style guide critic profile exists at the default location
    When I load the agent profile
    Then the profile has the correct QA metadata
    And the profile does not require scene_id
    And the profile has valid prompt templates for QA

  Scenario: Create QA agent from profile
    Given the style guide critic profile and prompt layers are loaded
    When I create a QA agent from the profile
    Then the agent can be used with the orchestrator

  Scenario: Profile validation allows QA variables
    Given a style guide critic profile with QA template variables
    When I load the agent profile
    Then the profile loads without validation errors
