# Standards Inventory & Analysis

This document categorizes the standards in `agent-os/standards/` by their reusability.

## 1. General Purpose Standards (Agent OS Stack)
These are universal best practices for modern Agentic AI development. They define the "Agent OS" way of building software: strict, verified, transparent, and architecturally clean.

| Standard | Category | Description |
|----------|----------|-------------|
| **python/modern-python-314** | Python | Use Python 3.14 features (unions, pattern matching). |
| **python/strict-typing-enforcement** | Python | No `Any`, strict Pydantic schemas. |
| **python/async-first-design** | Python | Async I/O for efficient LLM/Network ops. |
| **python/pydantic-only-schemas** | Python | Pydantic for all data boundaries (no dataclasses). |
| **architecture/api-response-format** | Architecture | Standardized `{data, error, meta}` envelope. |
| **architecture/log-line-format** | Architecture | Structured JSONL logs with consistent fields. |
| **architecture/naming-conventions** | Architecture | `snake_case` code, `PascalCase` types, `kebab-case` CLI. |
| **architecture/thin-adapter-pattern** | Architecture | Core logic is agnostic; surfaces (CLI/API) are thin IO wrappers. |
| **architecture/adapter-interface-protocol** | Architecture | Logic depends on Protocols (Ports), not implementations (Adapters). |
| **testing/three-tier-test-structure** | Testing | Strict `unit` (fast), `integration` (services), `quality` (LLMs) tiers. |
| **testing/test-timing-rules** | Testing | Performance budgets: <250ms, <5s, <30s. |
| **testing/bdd-for-integration-quality** | Testing | Gherkin-style Given/When/Then for high-level tests. |
| **testing/no-test-skipping** | Testing | Zero-skip policy; tests must pass or be fixed. |
| **testing/mandatory-coverage** | Testing | Tests must exercise actual behavior. |
| **testing/no-mocks-for-quality-tests** | Testing | Quality tier uses real LLMs; Integration mocks them. |
| **global/address-deprecations-immediately** | Maintenance | Zero-tolerance for deprecation warnings. |
| **global/prefer-dependency-updates** | Maintenance | Frequent updates; avoid pinning old versions. |
| **ux/frictionless-by-default** | UX | Guided setup and safe defaults. |
| **ux/progress-is-product** | UX | Immediate, unambiguous visibility of execution. |
| **ux/speed-with-guardrails** | UX | Fast iteration without breaking quality. |
| **ux/trust-through-transparency** | UX | "Glass box" execution; no silent failures. |

## 2. Project-Specific Standards
*None. All standards have been generalized to apply to any Agent OS project.*

## Summary
- **General Purpose**: 21 standards (100%)
- **Project Specific**: 0 standards (0%)
