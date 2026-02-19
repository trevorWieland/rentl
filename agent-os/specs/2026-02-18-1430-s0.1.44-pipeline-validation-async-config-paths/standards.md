# Standards: Pipeline Validation, Async Correctness & Config Paths

## Primary Standards (driving the violations)

1. **speed-with-guardrails** (`agent-os/standards/ux/speed-with-guardrails.md`)
   - Fast iterations without sacrificing determinism or quality
   - Relevant: edit output validation gates before persistence

2. **validate-generated-artifacts** (`agent-os/standards/testing/validate-generated-artifacts.md`)
   - Generated artifacts must validate against consuming component schemas, not just syntax
   - Relevant: all test assertions for configs/artifacts must use `model_validate`

3. **async-first-design** (`agent-os/standards/python/async-first-design.md`)
   - All I/O operations use async/await; no blocking operations in async paths
   - Relevant: wrap sync file I/O with `asyncio.to_thread` in async contexts

4. **config-path-resolution** (`agent-os/standards/architecture/config-path-resolution.md`)
   - Config paths resolve relative to config file parent, not CWD
   - Relevant: doctor and agent path resolver fixes

## Supporting Standards

5. **pydantic-only-schemas** (`agent-os/standards/python/pydantic-only-schemas.md`)
   - All schemas use Pydantic; relevant since fixes add `model_validate` calls

6. **make-all-gate** (`agent-os/standards/testing/make-all-gate.md`)
   - Full verification gate must pass
