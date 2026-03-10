# Standards: Initial Phase Agent — Pretranslation (Idiom Labeler)

## Applied Standards

### Testing Standards

- **testing/make-all-gate**: All code must pass `make all` verification before completion
- **testing/three-tier-test-structure**: Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- **testing/test-timing-rules**: Unit tests < 250ms, integration tests < 5s

### Python Standards

- **python/async-first-design**: Agent execution uses async/await patterns
- **python/strict-typing-enforcement**: All functions have type annotations
- **python/pydantic-only-schemas**: Input/output uses Pydantic models with `strict=True`

### Architecture Standards

- **architecture/adapter-interface-protocol**: Agent wrappers implement consistent interface
- **architecture/declarative-agent-config**: Agents defined via TOML, not code

### UX Standards

- **ux/frictionless-by-default**: Validation script works with rentl.toml defaults

## Verification Checklist

- [ ] `make all` passes
- [ ] Unit tests pass in < 250ms each
- [ ] Integration tests pass in < 5s each
- [ ] All functions have type annotations
- [ ] Pydantic models use `strict=True`
- [ ] Async patterns used for agent execution
