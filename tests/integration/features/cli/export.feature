Feature: Export Command
  As a user with translated lines
  I want to export them to various formats
  So that I can use the translations in my project

  Scenario: Export translated lines to CSV
    Given a JSONL file with translated lines
    When I export to CSV format
    Then the command succeeds
    And the output file contains all lines in CSV format

  Scenario: Export translated lines to TXT
    Given a JSONL file with translated lines
    When I export to TXT format
    Then the command succeeds
    And the output file contains all lines in TXT format

  Scenario: Export with untranslated lines errors by default
    Given a JSONL file with untranslated lines
    When I export with default untranslated policy
    Then the command returns an error response
    And the error code is "validation_error"
