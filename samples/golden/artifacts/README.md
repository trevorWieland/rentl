# Golden Artifacts Documentation

This directory contains golden artifacts for the sample VN script at `samples/golden/script.jsonl`.

## QA Category Coverage

The `qa.jsonl` file contains style guide violations that exercise all 8 QA categories defined in `rentl_schemas.primitives.QaCategory`:

1. **grammar** - Grammar-related issues (e.g., "Grammar: article usage")
2. **terminology** - Term consistency and usage (e.g., "Terminology: title consistency")
3. **style** - Stylistic preferences (e.g., "Style: question punctuation")
4. **consistency** - Internal consistency issues (e.g., "Consistency: honorific usage")
5. **formatting** - Presentation and formatting (e.g., "Formatting: sound effect presentation")
6. **context** - Context-dependent issues (e.g., "Context: scene atmosphere")
7. **cultural** - Cultural adaptation issues (e.g., "Cultural: sound effect adaptation")
8. **other** - Uncategorized issues

### Category Mapping Convention

Since `StyleGuideRuleViolation.rule_violated` is a free-text field, we use a prefix convention to enable programmatic category detection:

- Violations should be labeled as `"<Category>: <specific rule>"` (e.g., `"Grammar: article usage"`)
- For violations that don't clearly fit one category, use descriptive labels that map to the appropriate category (e.g., "Onomatopoeia formatting" → formatting)

Tests validating category coverage should parse the `rule_violated` field and extract the category prefix or infer the category from the rule description.

## Artifact Files

- `context.jsonl` - Scene summaries (SceneSummary per scene)
- `pretranslation.jsonl` - Idiom annotations for culturally-specific content
- `translate.jsonl` - English translations for all lines
- `qa.jsonl` - Style guide violations demonstrating QA capabilities
- `edit.jsonl` - Corrections applied based on QA findings
- `export.jsonl` - Final translated output
