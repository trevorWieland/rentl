Feature: Pretranslation Agent Quality
  As a localization team
  I want the pretranslation agent to identify idioms reliably
  So that translation handles tricky expressions correctly

  Scenario: Pretranslation agent produces correct structure
    Given a pretranslation agent structural eval dataset
    When I run the pretranslation agent structural evaluation
    Then the pretranslation agent structural evaluation passes

  Scenario: Pretranslation agent output passes LLM judge
    Given a pretranslation agent judge eval dataset
    When I run the pretranslation agent judge evaluation
    Then the pretranslation agent judge evaluation passes
