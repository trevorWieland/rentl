Feature: LLM Judge Evaluation
  As a benchmark user
  I want to evaluate translations using an LLM judge
  So that I can measure translation quality with structured rubric scores

  Scenario: Reference-based rubric evaluation
    Given a rubric judge with mocked LLM
    And translation lines
      | line_id | source     | translation |
      | line_1  | こんにちは | Hello       |
      | line_2  | さようなら | Goodbye     |
    And reference translations
      | line_id | reference |
      | line_1  | Hello     |
      | line_2  | Goodbye   |
    And judge responds with scores
      """
      accuracy: 5, style_fidelity: 4, consistency: 5
      """
    When I score translations with reference-based mode
    Then each line has scores for 3 dimensions
    And each dimension score includes reasoning
    And scores are in valid 1-5 range
    And each result includes source text and translation
    And each result includes reference translation

  Scenario: Reference-free rubric evaluation
    Given a rubric judge with mocked LLM
    And translation lines
      | line_id | source     | translation |
      | line_1  | こんにちは | Hello       |
      | line_2  | さようなら | Goodbye     |
    And judge responds with scores
      """
      accuracy: 4, style_fidelity: 3, consistency: 4
      """
    When I score translations with reference-free mode
    Then each line has scores for 3 dimensions
    And each dimension score includes reasoning
    And scores are in valid 1-5 range
    And each result includes source text and translation
    And each result does not include reference

  Scenario: Head-to-head comparison
    Given a rubric judge with mocked LLM
    And MTL translations
      | line_id | source     | translation     |
      | line_1  | こんにちは | Hello           |
      | line_2  | さようなら | Goodbye         |
    And rentl translations
      | line_id | source     | translation     |
      | line_1  | こんにちは | Hello there     |
      | line_2  | さようなら | See you later   |
    And judge responds with comparison
      """
      winner: B, reasoning: Translation B is more natural
      """
    When I compare translations head-to-head
    Then each comparison has a winner (A, B, or tie)
    And each comparison includes reasoning
    And each comparison includes both translations
    And dimension winners are tracked per comparison
