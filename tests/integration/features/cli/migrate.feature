Feature: Migrate Command
  As a user
  I want to migrate my config file to the current schema version
  So that my config stays compatible with new rentl versions

  Scenario: Migrate outdated config to current version
    Given a config file with an old schema version
    When I run the migrate command
    Then the command succeeds
    And the config file is migrated to the current version
    And a backup file is created
    And the output shows the migration plan

  Scenario: Migrate with dry-run shows plan without writing
    Given a config file with an old schema version
    When I run the migrate command with dry-run
    Then the command succeeds
    And the config file is unchanged
    And no backup file is created
    And the output shows the migration plan

  Scenario: Migrate already up-to-date config
    Given a config file with the current schema version
    When I run the migrate command
    Then the command succeeds
    And the output indicates the config is already up to date
    And no backup file is created

  Scenario: Auto-migrate on config load
    Given a config file with an old schema version
    When I load the config via run command
    Then the config is auto-migrated before validation
    And a backup file is created
    And the output shows auto-migration occurred
