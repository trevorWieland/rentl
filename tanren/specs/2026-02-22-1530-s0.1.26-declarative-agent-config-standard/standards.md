# Standards: s0.1.26 — Declarative Agent Config

## Applicable Standards

### Directly Relevant (core to the work)

1. **architecture/naming-conventions** — Agent names, config keys, schema names follow conventions
2. **architecture/config-path-resolution** — Config paths resolve relative to config file parent
3. **architecture/adapter-interface-protocol** — Agents access infrastructure through protocols, not directly
4. **python/pydantic-only-schemas** — All config schemas use Pydantic with Field and validators
5. **python/strict-typing-enforcement** — No Any/object in types
6. **global/no-placeholder-artifacts** — All artifacts functional and verified

### Testing Standards (for audit/fix tasks)

7. **testing/three-tier-test-structure** — Tests in unit/integration/quality folders
8. **testing/mandatory-coverage** — Coverage mandatory for features
9. **testing/validate-generated-artifacts** — Generated artifacts validate against schemas
