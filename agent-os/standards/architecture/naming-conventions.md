# Naming Conventions

Use consistent naming conventions across all code. Never mix styles.

```python
# ✓ Good: Consistent snake_case for modules/functions/variables
from translation_engine import translate_scene
from config_loader import load_config

def process_scene(scene: Scene) -> TranslationResult:
    """Process single scene."""
    result = translate_scene(scene)
    return result

# ✓ Good: PascalCase for classes/types
class TranslationRequest(BaseModel):
    """Translation request model."""

class VectorStoreProtocol(Protocol):
    """Vector store interface protocol."""

class SQLiteIndex:
    """SQLite run metadata index."""

# ✗ Bad: Inconsistent naming
from TranslationEngine import translate_Scene  # PascalCase for module
from config_loader import LoadConfig  # PascalCase for function

def ProcessScene(scene: Scene) -> TranslationResult:  # PascalCase for function
    ...

class translationRequest:  # snake_case for class
    pass
```

**Python code naming:**
- Modules/files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes/types: `PascalCase`
- Module-level constants: `SCREAMING_SNAKE_CASE` (immutable, module-scoped values)

**Module-level constants:**
Use `SCREAMING_SNAKE_CASE` for module-level constants — values that are immutable and defined at the top level of a module.

```python
# ✓ Good: SCREAMING_SNAKE_CASE for module-level constants
CURRENT_SCHEMA_VERSION = (0, 1, 0)
REQUIRED_COLUMNS = ("line_id", "text")
OPENROUTER_CAPABILITIES = ProviderCapabilities(
    supports_streaming=True,
    supports_tools=True,
)

# ✗ Bad: snake_case for module-level constants
current_schema_version = (0, 1, 0)  # should be SCREAMING_SNAKE_CASE
required_columns = ("line_id", "text")  # should be SCREAMING_SNAKE_CASE
```

**Database naming:**
- Tables/collections: `snake_case`
- Columns/fields: `snake_case`
- Foreign keys: `{entity}_id` (e.g., `run_id`, `scene_id`)

**API naming:**
- CLI commands: `kebab-case` (e.g., `run-pipeline`, `show-status`)
- CLI options: `--snake-case` (e.g., `--run-id`, `--config-file`)

**JSON/JSONL naming:**
- Fields: `snake_case` (e.g., `run_id`, `phase_name`, `error_message`)

**Event naming:**
- Event names: `snake_case` (e.g., `run_started`, `phase_completed`, `translation_finished`)
- Log event names (JSONL `event`) must be `snake_case`
- When phase-specific, prefix with phase name (e.g., `translate_completed`, `qa_failed`)

**Why:** Consistency makes code predictable and easier to navigate; reduces confusion when multiple developers/agents work together.
