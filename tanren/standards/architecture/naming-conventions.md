# Naming Conventions

Use consistent naming conventions across all code. Never mix styles.

```python
# ✓ Good: Consistent snake_case for modules/functions/variables
from task_engine import process_item
from config_loader import load_config


def handle_item(item: Item) -> TaskResult:
    """Process single item."""
    result = process_item(item)
    return result


# ✓ Good: PascalCase for classes/types
class TaskRequest(BaseModel):
    """Task request model."""


class VectorStoreProtocol(Protocol):
    """Vector store interface protocol."""


class SQLiteIndex:
    """SQLite run metadata index."""


# ✗ Bad: Inconsistent naming
from TaskEngine import process_Item  # PascalCase for module
from config_loader import LoadConfig  # PascalCase for function


def ProcessItem(item: Item) -> TaskResult:  # PascalCase for function
    ...


class taskRequest:  # snake_case for class
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
    name="OpenRouter",
    is_openrouter=True,
    supports_tool_calling=True,
    supports_tool_choice_required=True,
)

# ✗ Bad: snake_case for module-level constants
current_schema_version = (0, 1, 0)  # should be SCREAMING_SNAKE_CASE
required_columns = ("line_id", "text")  # should be SCREAMING_SNAKE_CASE
```

**Database naming:**
- Tables/collections: `snake_case`
- Columns/fields: `snake_case`
- Foreign keys: `{entity}_id` (e.g., `run_id`, `item_id`)

**API naming:**
- CLI commands: `kebab-case` (e.g., `run-pipeline`, `show-status`)
- CLI options: `--snake-case` (e.g., `--run-id`, `--config-file`)

**JSON/JSONL naming:**
- Fields: `snake_case` (e.g., `run_id`, `phase_name`, `error_message`)

**Event naming:**
- Event names: `snake_case` (e.g., `run_started`, `phase_completed`, `processing_finished`)
- Log event names (JSONL `event`) must be `snake_case`
- When phase-specific, prefix with phase name (e.g., `process_completed`, `validate_failed`)

**Why:** Consistency makes code predictable and easier to navigate; reduces confusion when multiple developers/agents work together.
