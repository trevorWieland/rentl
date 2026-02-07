Feature: Init Command
  As a new user
  I want to bootstrap a rentl project
  So that I can start translating immediately after setting an API key

  Scenario: Init produces runnable project
    Given an empty temp directory
    When I generate a project with default answers
    Then the command succeeds
    And all expected files exist
    And the generated config validates
    And the generated config resolves without errors
    And the seed data file is valid JSONL
