# Shape: Initial Phase Agent — Pretranslation (Idiom Labeler)

## Appetite

Small batch — targeted implementation following established patterns from Context phase.

## Problem

The Pretranslation phase needs its first agent to demonstrate the phase's role in the pipeline. Idiom identification is a natural choice as it:
- Clearly belongs in pretranslation (before actual translation)
- Produces annotations consumed by downstream translation agents
- Has well-defined output semantics
- Can work without scene boundaries (unlike SceneSummarizer)

## Solution

Create an Idiom Labeler agent that:
1. Follows the TOML-based declarative pattern from SceneSummarizer
2. Works on batches/chunks rather than scenes
3. Produces `IdiomAnnotation` records that convert to `PretranslationAnnotation`
4. Provides translation hints for identified idioms

## Rabbit Holes

- **Scope creep to other annotation types**: This spec covers ONLY idiom labeling. Other pretranslation tasks (terminology extraction, length warnings, etc.) are separate agents.
- **Real-time idiom detection accuracy**: The spec does not require perfect idiom detection. The goal is demonstrating the pretranslation pattern.
- **Complex chunking strategies**: Simple fixed-size chunking is sufficient for v1.

## No-Gos

- No changes to the base ProfileAgent runtime
- No new template variables beyond the pretranslation set
- No interactive/streaming output
- No batching optimizations (concurrent chunk processing is v0.2)

## Context

The Context phase's SceneSummarizer established patterns for:
- TOML-based agent profiles
- Three-layer prompt composition
- Schema registry and validation
- Factory functions for agent creation
- Validation scripts for manual testing

This spec applies those same patterns to Pretranslation, demonstrating phase-agnostic reusability.
