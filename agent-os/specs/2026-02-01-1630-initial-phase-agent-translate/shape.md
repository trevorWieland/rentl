# Shape: Initial Phase Agent — Translate (Direct Translator)

## Appetite

Small batch — targeted implementation following established patterns from Context and Pretranslation phases.

## Problem

The Translate phase needs its first agent to produce translated text. This agent:
- Consumes context from upstream phases (scene summaries, idiom annotations)
- Produces `TranslatedLine` records for downstream QA and Edit phases
- Enables configurable language pairs
- Follows the established TOML-based declarative pattern

## Solution

Create a Direct Translator agent that:
1. Follows the TOML-based declarative pattern from SceneSummarizer and IdiomLabeler
2. Works on batches/chunks (like IdiomLabeler)
3. Consumes scene summaries, pretranslation annotations, and glossary terms
4. Produces `TranslationResult` records that convert to `TranslatedLine`

## Rabbit Holes

- **Scope creep to advanced translation features**: This spec covers ONLY simple direct translation. Features like MTL model tool calls, ensemble approaches, or retrieval-augmented translation are future agents.
- **Translation quality optimization**: The spec does not require perfect translation. The goal is demonstrating the translate pattern.
- **Complex chunking strategies**: Simple fixed-size chunking is sufficient for v1.

## No-Gos

- No changes to the base ProfileAgent runtime
- No new template variables beyond the translate set (already defined in templates.py)
- No interactive/streaming output
- No batching optimizations (concurrent chunk processing is v0.2)
- No MTL model tool calls (future agent feature)

## Context

The Context phase's SceneSummarizer and Pretranslation phase's IdiomLabeler established patterns for:
- TOML-based agent profiles
- Three-layer prompt composition
- Schema registry and validation
- Factory functions for agent creation
- Validation scripts for manual testing

This spec applies those same patterns to Translate, demonstrating phase-agnostic reusability.

## Decisions

- **Agent name**: `direct_translator` to distinguish from future advanced translation agents
- **Chunk size**: 50 lines (matches pretranslation default)
- **Template variables**: Use existing `TRANSLATE_AGENT_VARIABLES` set
- **Output format**: `TranslationResult` wrapping `TranslationResultLine` list

## Standards Applied

- testing/make-all-gate — Verification required before completion
- testing/three-tier-test-structure — Unit/integration test folders
- python/async-first-design — Agent execution is async
- python/pydantic-only-schemas — All I/O uses Pydantic
