Feature: Deterministic QA Integration
  As a developer running deterministic QA checks
  I want the full QA runner to detect formatting issues
  So that translation quality is enforced automatically

  Scenario: Lines with issues are detected
    Given translated lines with formatting issues
    And a QA runner configured for line length and unsupported characters
    When I run QA checks
    Then issues are detected for problematic lines
    And clean lines have no issues

  Scenario: Clean lines produce no issues
    Given clean translated lines
    And a QA runner configured for line length and unsupported characters
    When I run QA checks
    Then no issues are reported

  Scenario: Runner respects check enable/disable config
    Given a DeterministicQaConfig with one enabled and one disabled check
    And translated lines with issues for both checks
    When I build a runner from config and run checks
    Then only the enabled check produces issues
    And severities match the configuration

  Scenario: Unsupported characters are detected with details
    Given translated lines with characters outside ASCII range
    And a QA runner configured for ASCII-only characters
    When I run QA checks
    Then non-ASCII lines are flagged
    And issue metadata includes character details

  Scenario: Issues have correct category and structure
    Given translated lines with various formatting issues
    And a QA runner configured for line length and unsupported characters
    When I run QA checks
    Then all issues have FORMATTING category
    And all issues have valid structure
