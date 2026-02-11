Feature: Benchmark Eval Set Download
  As a rentl user
  I want to download and validate eval set source material
  So that I can prepare benchmark evaluations

  Scenario: Download a single script with hash validation
    Given a mock HTTP server with a valid script
    When I download the script with correct hash
    Then the script is cached to disk
    And the script content matches

  Scenario: Download fails when hash validation fails
    Given a mock HTTP server with a valid script
    When I download the script with wrong hash
    Then the download raises a hash validation error
    And the cached file is removed

  Scenario: Download uses cache when available
    Given a script is already cached with correct hash
    When I attempt to download the script
    Then the HTTP server is not called
    And the cached script is returned

  Scenario: Download multiple scripts with progress tracking
    Given a mock HTTP server with multiple scripts
    When I download all scripts
    Then each script is downloaded successfully
    And progress callbacks are invoked in order

  Scenario: Download propagates HTTP errors
    Given a mock HTTP server that returns 404
    When I attempt to download a missing script
    Then the download raises an HTTP error

  Scenario: Download enforces manifest coverage
    Given a hash manifest that excludes a script
    When I attempt to download the excluded script
    Then the download raises a manifest coverage error

  Scenario: End-to-end download, parse, and align flow
    Given a mock HTTP server with Japanese and English scripts
    When I download both scripts
    And I parse both scripts with RenpyDialogueParser
    And I align the parsed lines
    Then the aligned output contains paired source and reference lines

  Scenario: Downloaded JSONL is pipeline-ingestable
    Given a mock HTTP server with a valid script
    When I download the script with correct hash
    And I parse the script with RenpyDialogueParser
    And I serialize the parsed lines to JSONL
    Then the JSONL can be loaded by the ingest adapter
