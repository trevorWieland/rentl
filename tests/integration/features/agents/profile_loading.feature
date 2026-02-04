Feature: Profile Agent Loading
  As a developer
  I want to load agent profiles from TOML files
  So that agents can be configured declaratively

  Scenario: Load scene summarizer profile
    Given a scene summarizer profile exists at the default location
    When I load the agent profile
    Then the profile has the correct metadata
    And the profile requires scene_id
    And the profile has valid prompt templates

  Scenario: Profile validation catches unknown variables
    Given an agent profile with unknown template variables
    When I attempt to load the agent profile
    Then an error is raised mentioning the unknown variables

  Scenario: Create context agent from profile
    Given the scene summarizer profile and prompt layers are loaded
    When I create a context agent from the profile
    Then the agent can be used with the orchestrator

  Scenario: Scene validation rejects lines without scene_id
    Given a context agent created from profile
    And source lines without scene_id
    When I run the agent
    Then a SceneValidationError is raised
    And the error suggests using BatchSummarizer
