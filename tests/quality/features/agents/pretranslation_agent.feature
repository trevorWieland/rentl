Feature: Pretranslation Agent Quality
  As a localization team
  I want the pretranslation agent to identify idioms reliably
  So that translation handles tricky expressions correctly

  Scenario: Pretranslation agent evaluation passes
    Given a pretranslation agent quality eval dataset
    When I run the pretranslation agent quality evaluation
    Then the pretranslation agent evaluation passes
