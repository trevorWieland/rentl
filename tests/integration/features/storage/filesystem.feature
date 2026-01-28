Feature: FileSystem Storage Adapters
  As a developer using storage adapters
  I want to persist and retrieve run state and artifacts
  So that pipeline runs are durable and auditable

  Scenario: RunStateStore save and load round-trip
    Given an empty workspace directory
    When I save a run state to the store
    And I load the run state by ID
    Then the loaded state matches the saved state

  Scenario: ArtifactStore JSONL write and read round-trip
    Given an empty workspace directory
    When I write a JSONL artifact with records
    And I read the artifact back
    Then the records match the originals

  Scenario: LogStore run log persistence
    Given an empty workspace directory
    When I write log events to a run
    And I get the log reference
    Then the log file exists at the referenced path
