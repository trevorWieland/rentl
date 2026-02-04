Feature: Direct Translator Profile Loading
  As a developer
  I want to load direct translator profiles from TOML files
  So that agents can be configured declaratively

  Scenario: Load direct translator profile
    Given a direct translator profile exists at the default location
    When I load the agent profile
    Then the profile has the correct translate metadata
    And the profile does not require scene_id
    And the profile has valid prompt templates for translate

  Scenario: Create translate agent from profile
    Given the direct translator profile and prompt layers are loaded
    When I create a translate agent from the profile
    Then the agent can be used with the orchestrator

  Scenario: Profile validation allows translate variables
    Given a direct translator profile with translate template variables
    When I load the agent profile
    Then the profile loads without validation errors
