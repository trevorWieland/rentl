Feature: Context Agent Quality
  As a localization team
  I want the context agent to produce reliable summaries
  So that downstream phases have trustworthy context

  Scenario: Context agent evaluation passes
    Given a context agent quality eval dataset
    When I run the context agent quality evaluation
    Then the context agent evaluation passes
