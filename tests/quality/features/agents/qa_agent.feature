Feature: QA Agent Quality
  As a localization team
  I want the QA agent to flag style guide issues reliably
  So that edits can be targeted and accurate

  Scenario: QA agent evaluation passes
    Given a QA agent quality eval dataset
    When I run the QA agent quality evaluation
    Then the QA agent evaluation passes
