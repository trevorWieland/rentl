# Quality Test Suite - Plan

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-02-1545-quality-test-suite/` with:
- **plan.md** - This full plan
- **shape.md** - Shaping notes (scope, decisions, context)
- **standards.md** - Relevant standards that apply to this work
- **references.md** - Pointers to reference implementations studied
- **visuals/** - Any mockups or screenshots provided

## Task 2: Research pydantic-evals best practices and map to implementation

- Review pydantic-evals core concepts and LLM-judge guidance for rubric design
- Incorporate best practices:
  - Specific rubrics with multiple judges per quality dimension
  - Deterministic checks before LLM judges
  - Temperature 0 for judge consistency
  - Dataset-level vs case-level evaluators
  - Capture evaluation reasons for debugging and prompt iteration
- Identify any pydantic-ai integration changes needed for clean evaluation

## Task 3: Quality eval foundation (pydantic-evals)

- Add `pydantic-evals` as a test dependency
- Create a shared eval harness under `tests/quality/` using datasets/cases/experiments
- Add env-driven config for model/base_url/API key (no logging of secrets)
- Enforce test tier rules: BDD-style, no mocks, real LLMs, <30s per test
- Provide a simple CLI or pytest entry for running quality evals

## Task 4: Tool-call instrumentation and evaluators

- Add test-only tool wrappers for `context_lookup`, `glossary_search`,
  `style_guide_lookup` that record calls and validate input/output formats
- Create deterministic evaluators for:
  - Tool call presence when required
  - Tool input schema compliance
  - Tool output schema compliance
- Capture call logs in evaluation reports (attributes/metrics)

## Task 5: Five-agent quality eval suites

- Build minimal datasets for all five agents:
  - Context
  - Pretranslation
  - Translate
  - QA
  - Edit
- Keep inputs tiny to ensure runtime <30s
- Use evaluators that check:
  - Schema validity and required fields
  - Correct target language (LLM-as-judge rubric)
  - Tool usage and formatting (deterministic)
  - Task-specific expectations (lenient thresholds initially)
- Set pass/fail thresholds for each dataset and case

## Task 6: Reliability fixes from eval feedback

- Run evals and capture failures with reasons
- Adjust prompts/profiles and runtime usage to improve reliability
- Avoid blaming the model; use prompt improvements or schema adjustments
- Iterate until all five agent suites meet the lenient thresholds

## Task 7: Documentation

- Document how to run quality evals and required env vars
- Include expected runtime and cost guidance
- Reiterate no-skipping policy for quality tests

## Task 8: Verification - Run make all

Run `make all` to ensure all code passes quality checks:
- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests

This task MUST pass before the spec is considered complete. Failures must be
fixed and re-run until `make all` passes.
