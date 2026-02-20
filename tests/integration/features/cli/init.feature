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
    And the pipeline can execute end-to-end and produce export artifacts

  Scenario: Environment variable scoping is isolated
    Given an empty temp directory with generated project
    When I build agent pools within a scoped env override
    Then the env var is restored after scope exit

  Scenario: All endpoint presets produce valid configs
    Given all endpoint presets with default models
    When I generate and validate each preset config
    Then each config passes schema validation
    And agent pools can be built from each config
