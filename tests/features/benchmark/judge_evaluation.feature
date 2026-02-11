Feature: LLM Judge Evaluation
  As a benchmark user
  I want to evaluate translations using an LLM judge
  So that I can measure translation quality with head-to-head comparison

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

  Scenario: Head-to-head comparison with randomized order
    Given a rubric judge with mocked LLM
    And MTL translations
      | line_id | source     | translation |
      | line_1  | こんにちは | Hello       |
    And rentl translations
      | line_id | source     | translation   |
      | line_1  | こんにちは | Hello there   |
    And judge responds with winner A
      """
      winner: A, reasoning: Translation A is more accurate
      accuracy: A, style_fidelity: B, consistency: B
      """
    When I compare translations head-to-head with randomization
    Then randomization remaps winners correctly
    And each comparison has a winner (A, B, or tie)
    And dimension winners are tracked per comparison
