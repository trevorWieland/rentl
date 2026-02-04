Feature: Translate Agent Quality
  As a localization team
  I want the translate agent to produce accurate translations
  So that users receive understandable output

  Scenario: Translate agent evaluation passes
    Given a translate agent quality eval dataset
    When I run the translate agent quality evaluation
    Then the translate agent evaluation passes
