Feature: Idiom Labeler Profile Loading
  As a developer
  I want to load idiom labeler profiles from TOML files
  So that agents can be configured declaratively

  Scenario: Load idiom labeler profile
    Given an idiom labeler profile exists at the default location
    When I load the agent profile
    Then the profile has the correct pretranslation metadata
    And the profile does not require scene_id
    And the profile has valid prompt templates for pretranslation

  Scenario: Create pretranslation agent from profile
    Given the idiom labeler profile and prompt layers are loaded
    When I create a pretranslation agent from the profile
    Then the agent can be used with the orchestrator

  Scenario: Profile validation allows pretranslation variables
    Given an idiom labeler profile with pretranslation template variables
    When I load the agent profile
    Then the profile loads without validation errors
