Feature: Doctor Auto-Migration
  As a developer with an outdated config file
  I want the doctor module to auto-migrate my config
  So that I can upgrade seamlessly without manual edits

  Scenario: Outdated config is auto-migrated
    Given a config file with old schema version 0.0.1
    When I run check_config_valid
    Then the check passes
    And a backup file is created
    And the backup contains the old version
    And the migrated config has version 0.1.0

  Scenario: Current config requires no migration
    Given a config file with current schema version 0.1.0
    When I run check_config_valid
    Then the check passes
    And no backup file is created
    And the config version is unchanged
