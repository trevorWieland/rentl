Feature: Run Pipeline Command
  As a user with a configured project
  I want to run the translation pipeline
  So that my content gets translated

  Scenario: Run pipeline with ingest phase only
    Given a rentl config with ingest phase enabled
    And an input file with source lines
    When I run the pipeline command
    Then the command succeeds
    And the response contains run data

  Scenario: Run pipeline with missing input file
    Given a rentl config with ingest phase enabled
    And no input file exists
    When I run the pipeline command
    Then the command returns an error response
