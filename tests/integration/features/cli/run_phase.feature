Feature: Run Phase Command
  As a user with a configured project
  I want to run a specific pipeline phase
  So that I can control the translation process step by step

  Scenario: Run ingest phase only
    Given a rentl config with all phases configured
    And an input file with source lines for phase test
    When I run the ingest phase
    Then the command succeeds
    And the response contains phase run data

  Scenario: Run export phase requires target language
    Given a rentl config with all phases configured
    And no prior run state exists
    When I run the export phase without target language
    Then the command returns an error response
