# Standards: LLM Provider Abstraction & Agent Wiring

## Applicable Standards

### Primary (from audit)

1. **openrouter-provider-routing** — Validate OpenRouter provider compatibility before pipeline runs; use provider-qualified model IDs and whitelists
   - Path: `agent-os/standards/architecture/openrouter-provider-routing.md`
   - Audit score: 42/100 (High priority)

2. **adapter-interface-protocol** — Never access infrastructure adapters directly; access protocols defined in the Core Domain
   - Path: `agent-os/standards/architecture/adapter-interface-protocol.md`
   - Audit score: 82/100 (High priority)

3. **agent-tool-registration** — Register tools with explicit names via pydantic_ai.Tool to prevent prompt/tool mismatches
   - Path: `agent-os/standards/global/agent-tool-registration.md`
   - Audit score: 72/100 (High priority)

4. **pydantic-ai-structured-output** — All LLM calls must use pydantic-ai Agent with output_type; never hand-roll JSON parsing
   - Path: `agent-os/standards/global/pydantic-ai-structured-output.md`
   - Audit score: 76/100 (High priority)

5. **batch-alignment-feedback** — Batch agents must verify output IDs match input IDs; provide structured retry feedback on mismatch
   - Path: `agent-os/standards/global/batch-alignment-feedback.md`
   - Audit score: 74/100 (High priority)

### Supporting

6. **strict-typing-enforcement** — Never use Any or object in types; all Pydantic fields use Field with description and built-in validators
   - Path: `agent-os/standards/python/strict-typing-enforcement.md`

7. **pydantic-only-schemas** — Never use dataclasses or plain classes; all schemas must use Pydantic with Field and validators
   - Path: `agent-os/standards/python/pydantic-only-schemas.md`

8. **mock-execution-boundary** — Mock at the actual execution boundary per test tier; verify mocks are invoked
   - Path: `agent-os/standards/testing/mock-execution-boundary.md`
