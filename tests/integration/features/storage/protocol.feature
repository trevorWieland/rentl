Feature: Storage Protocol Compliance
  As a developer implementing storage adapters
  I want to verify that adapters implement the defined protocols
  So that different backends can be swapped without breaking the system

  Background:
    Given an empty workspace directory

  # RunStateStoreProtocol compliance tests

  Scenario: FileSystemRunStateStore implements RunStateStoreProtocol
    Given a FileSystemRunStateStore instance
    Then the store implements RunStateStoreProtocol

  Scenario: RunStateStore save_run_index and list_run_index round-trip
    Given a FileSystemRunStateStore instance
    When I save a run index record
    And I list run index records
    Then the saved index record appears in the list

  Scenario: RunStateStore list_run_index filters by status
    Given a FileSystemRunStateStore instance
    When I save run index records with different statuses
    And I list run index records filtered by pending status
    Then only pending records are returned

  # ArtifactStoreProtocol compliance tests

  Scenario: FileSystemArtifactStore implements ArtifactStoreProtocol
    Given a FileSystemArtifactStore instance
    Then the store implements ArtifactStoreProtocol

  Scenario: ArtifactStore write_artifact_json and load_artifact_json round-trip
    Given a FileSystemArtifactStore instance
    When I write a JSON artifact
    And I load the JSON artifact
    Then the loaded artifact matches the original

  Scenario: ArtifactStore list_artifacts returns artifacts for run
    Given a FileSystemArtifactStore instance
    When I write multiple artifacts for a run
    And I list artifacts for the run
    Then all artifacts are returned in the list

  # LogStoreProtocol compliance tests

  Scenario: FileSystemLogStore implements LogStoreProtocol
    Given a FileSystemLogStore instance
    Then the store implements LogStoreProtocol

  Scenario: LogStore append_log single entry
    Given a FileSystemLogStore instance
    When I append a single log entry
    And I get the log reference
    Then the log file contains the entry
