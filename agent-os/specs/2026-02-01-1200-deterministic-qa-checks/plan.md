# Spec (18) Initial QA Checks (Deterministic)

## Summary

Implement deterministic QA checks that identify formatting and completeness issues without LLM reasoning. These checks **annotate lines** with issues that signal to the Editor phase what needs fixing. They do not fail the pipeline — critical issues at most prevent that specific line from being included in the exported patch.

## Pipeline Context

```
Context → Pretranslation → Translate → QA (detect issues) → Edit (fix issues) → QA → ... until clean
```

- **Spec 18 (this):** Deterministic checks for formatting issues (line length, invalid chars, empty, whitespace)
- **Spec 19:** LLM-based checks for conceptual issues (prose mismatch, style guide, pronouns)
- **Editor phase:** Takes QA issues and generates corrected translations
- **Export:** May exclude lines with unresolved critical issues from the patch

## Scope Decisions

- **Core formatting checks only:**
  - Line length limits (configurable, no default)
  - Unsupported characters (configurable allowlist)
  - Empty translated lines
  - Leading/trailing whitespace issues
- **Output:** Issues go to `QaPhaseOutput.issues` as `QaIssue` entries
- **No pipeline failure:** Issues are annotations, not blockers

---

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-01-1200-deterministic-qa-checks/` with:
- `plan.md` — This plan
- `shape.md` — Shaping decisions and context
- `standards.md` — Applicable standards
- `references.md` — Reference implementations

---

## Task 2: Add Configuration Schemas

**File:** `packages/rentl-schemas/src/rentl_schemas/config.py`

Add new Pydantic schemas for configuring deterministic checks:

```python
class DeterministicQaCheckConfig(BaseSchema):
    """Configuration for a single deterministic QA check."""
    check_name: str = Field(..., description="Check identifier (e.g., 'line_length')")
    enabled: bool = Field(True, description="Whether this check runs")
    severity: QaSeverity = Field(..., description="Severity for issues from this check")
    parameters: dict[str, JsonValue] | None = Field(None, description="Check-specific params")

class DeterministicQaConfig(BaseSchema):
    """Configuration for the deterministic QA check suite."""
    enabled: bool = Field(True, description="Enable deterministic QA checks")
    checks: list[DeterministicQaCheckConfig] = Field(..., description="Configured checks")
```

---

## Task 3: Create QA Check Framework

**New directory:** `packages/rentl-core/src/rentl_core/qa/`

### 3a. Protocol and Result Types

**File:** `packages/rentl-core/src/rentl_core/qa/protocol.py`

```python
@dataclass(frozen=True, slots=True)
class DeterministicCheckResult:
    """Result of a single check on a single line."""
    line_id: LineId
    category: QaCategory
    severity: QaSeverity
    message: str
    suggestion: str | None = None
    metadata: dict[str, JsonValue] | None = None

@runtime_checkable
class DeterministicCheck(Protocol):
    """Protocol for deterministic QA checks."""

    @property
    def check_name(self) -> str: ...

    @property
    def category(self) -> QaCategory: ...

    def configure(self, parameters: dict[str, JsonValue] | None) -> None: ...

    def check_line(self, line: TranslatedLine, severity: QaSeverity) -> list[DeterministicCheckResult]: ...
```

### 3b. Check Registry

**File:** `packages/rentl-core/src/rentl_core/qa/registry.py`

- `CheckRegistry` class with `register()`, `create()`, `list_checks()` methods
- `get_default_registry()` factory returning registry with all built-in checks

### 3c. Runner

**File:** `packages/rentl-core/src/rentl_core/qa/runner.py`

```python
class DeterministicQaRunner:
    """Runner for deterministic QA checks."""

    def configure_check(self, check_name: str, severity: QaSeverity, parameters: dict | None) -> None:
        """Configure and add a check to the runner."""
        ...

    def run_checks(self, translated_lines: list[TranslatedLine]) -> list[QaIssue]:
        """Run all configured checks, return issues found."""
        ...
```

---

## Task 4: Implement Individual Checks

**Directory:** `packages/rentl-core/src/rentl_core/qa/checks/`

### 4a. Line Length Check
**File:** `line_length.py`
- Parameters: `max_length: int` (required), `count_mode: "characters" | "bytes"` (default: characters)
- Category: `FORMATTING`
- Detects lines exceeding configured length

### 4b. Empty Translation Check
**File:** `empty_translation.py`
- No parameters
- Category: `FORMATTING`
- Detects empty or whitespace-only translations

### 4c. Whitespace Check
**File:** `whitespace.py`
- No parameters
- Category: `FORMATTING`
- Detects leading/trailing whitespace (separate issues for each)

### 4d. Unsupported Characters Check
**File:** `unsupported_chars.py`
- Parameters: `allowed_ranges: list[str]` (e.g., `["U+0000-U+007F", "U+3000-U+30FF"]`), `allow_common_punctuation: bool` (default: true)
- Category: `FORMATTING`
- Detects characters outside the allowed set

---

## Task 5: Integrate with Orchestrator

**File:** `packages/rentl-core/src/rentl_core/orchestrator.py`

Modify QA phase execution to run deterministic checks:

1. Extract `DeterministicQaConfig` from phase parameters
2. Build runner and run checks on `translated_lines`
3. Convert results to `QaIssue` entries
4. Merge with any LLM-based QA issues into final `QaPhaseOutput`
5. Rebuild `QaSummary` with combined counts

Helper functions:
- `_get_deterministic_qa_config(config) -> DeterministicQaConfig | None`
- `_build_deterministic_qa_runner(config) -> DeterministicQaRunner`
- `_merge_deterministic_issues(output, issues) -> QaPhaseOutput`

**Note:** No failure logic — issues are added to output, pipeline continues.

---

## Task 6: Unit Tests

**Directory:** `tests/unit/core/qa/`

### 6a. Test Individual Checks
- `test_line_length.py` — length exceeded/within bounds, count modes, edge cases
- `test_empty_translation.py` — empty string, whitespace-only, valid text
- `test_whitespace.py` — leading ws, trailing ws, both, neither
- `test_unsupported_chars.py` — allowlist parsing, range formats, character detection

### 6b. Test Runner
- `test_runner.py` — multi-check execution, configuration validation, result aggregation

### 6c. Test Registry
- `test_registry.py` — registration, factory creation, unknown check error

---

## Task 7: Integration Tests

**File:** `tests/integration/core/test_deterministic_qa.py`

BDD-style tests:
- Given translated lines with formatting issues, when running deterministic QA, then issues are included in output
- Given mixed issues (deterministic + LLM-based), when QA completes, then both appear in `QaPhaseOutput`
- Given no issues, when running deterministic QA, then output has empty issues list

---

## Task 8: Verification - Run make all

Run `make all` to ensure all code passes quality checks:
- Format code with ruff
- Check linting rules
- Type check with ty
- Run unit tests

This task MUST pass before the spec is considered complete.

---

## Critical Files

| File | Action |
|------|--------|
| `packages/rentl-schemas/src/rentl_schemas/config.py` | Add DeterministicQaConfig, DeterministicQaCheckConfig |
| `packages/rentl-core/src/rentl_core/qa/` | New module (protocol, registry, runner) |
| `packages/rentl-core/src/rentl_core/qa/checks/` | Individual check implementations |
| `packages/rentl-core/src/rentl_core/orchestrator.py` | Integrate runner into QA phase |
| `packages/rentl-schemas/src/rentl_schemas/qa.py` | Reference only (QaIssue schema) |

---

## Configuration Example

```toml
[[pipeline.phases]]
phase = "qa"

[pipeline.phases.parameters.deterministic]
enabled = true

[[pipeline.phases.parameters.deterministic.checks]]
check_name = "line_length"
severity = "critical"  # Critical = may block export
parameters = { max_length = 256, count_mode = "characters" }

[[pipeline.phases.parameters.deterministic.checks]]
check_name = "empty_translation"
severity = "critical"

[[pipeline.phases.parameters.deterministic.checks]]
check_name = "whitespace"
severity = "minor"  # Minor = cosmetic, low priority for editor

[[pipeline.phases.parameters.deterministic.checks]]
check_name = "unsupported_characters"
severity = "critical"
parameters = { allowed_ranges = ["U+0000-U+007F"], allow_common_punctuation = true }
```

---

## Standards Applied

- **testing/make-all-gate** — Verification required before completion
- **testing/three-tier-test-structure** — Unit (<250ms), integration (<5s)
- **testing/bdd-for-integration-quality** — Given/When/Then for integration tests
- **python/pydantic-only-schemas** — All config schemas use Pydantic
- **python/strict-typing-enforcement** — No `Any`, all fields with Field descriptions
- **architecture/thin-adapter-pattern** — Checks are pure logic, orchestrator is thin integration
