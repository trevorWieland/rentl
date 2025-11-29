# rentl-core: Data Models, I/O, and Configuration

Core data structures, loaders, and configuration for the rentl translation pipeline.

---

## Purpose

`rentl-core` provides the foundation for all other rentl packages:

- **Data models**: Pydantic models for metadata and scene data with provenance tracking
- **I/O utilities**: Async JSONL/JSON loaders and writers using `orjson` + `anyio`
- **Configuration**: Project settings and LLM backend configuration via `pydantic-settings`
- **Project context**: Runtime state management for metadata and scenes

---

## Scope

### In Scope

- Pydantic models matching [SCHEMAS.md](../../SCHEMAS.md) specifications
- Async loaders for all metadata formats (game, characters, glossary, locations, routes, scenes)
- Async scene file loaders (input/scenes/*.jsonl)
- Project context class for in-memory metadata access
- Settings management (environment variables, .env support)

### Out of Scope

- Agent logic (belongs in `rentl-agents`)
- Orchestration workflows (belongs in `rentl-pipelines`)
- CLI commands (belongs in `rentl-cli`)
- LLM interactions (LLM wrappers belong in `rentl-agents`)

---

## Key Modules

### model/

Pydantic models with provenance tracking:

```
model/
  game.py         # GameMetadata, UIConstraints
  character.py    # CharacterMetadata
  glossary.py     # GlossaryEntry
  location.py     # LocationMetadata
  route.py        # RouteMetadata
  scene.py        # SceneMetadata, SceneAnnotations
  line.py         # SourceLine, TranslatedLine
```

**Design principles**:
- All models use `extra="allow"` for custom fields
- Provenance fields (`*_origin`) for trackable content
- Clear field descriptions with examples in docstrings

### io/

Async I/O utilities:

```
io/
  loader.py       # Async loaders for all metadata formats
  writer.py       # Async writers for metadata and translations
```

**Design principles**:
- Use `orjson` for fast JSON parsing
- Use `anyio` for async file operations
- Return typed Pydantic models (validation happens in loader)
- Parallel loading where beneficial (e.g., `load_all_scene_files`)

### config/

Configuration and settings:

```
config/
  settings.py     # Environment-based settings (LLM, Tavily, LangSmith)
  project.py      # (Future) Per-game project config from rentl.project.toml
```

**Design principles**:
- Use `pydantic-settings` for env var loading
- Support `.env` files
- Required settings raise clear errors if missing

### context/

Runtime project state:

```
context/
  project.py      # ProjectContext model
```

**Design principles**:
- Load all metadata once at startup into memory
- Provide fast lookup methods (e.g., `get_character(id)`)
- Async methods for file I/O (loading scenes, saving metadata)
- Immutable after loading (modifications require explicit save)

---

## Design Patterns

### Provenance Tracking

All content fields include corresponding `*_origin` fields:

```python
class CharacterMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique character identifier")
    name_src: str = Field(..., description="Name in source language")
    name_src_origin: str | None = Field(default=None)  # Provenance
    name_tgt: str | None = Field(default=None, description="Localized name")
    name_tgt_origin: str | None = Field(default=None)  # Provenance
    pronouns: str | None = Field(default=None)
    pronouns_origin: str | None = Field(default=None)  # Provenance
    notes: str | None = Field(default=None)
    notes_origin: str | None = Field(default=None)  # Provenance
```

**Rules**:
- Origin fields are **required** if the corresponding content field is non-null
- Origin format: `"human"` or `"agent:<subagent_name>:<YYYY-MM-DD>"`
- Fields without provenance tracking: `id`, structural fields, engine-specific config

See [SCHEMAS.md](../../SCHEMAS.md) for complete provenance documentation.

### Async I/O

All I/O operations are async:

```python
# ✅ Good: Async loading
async def load_project_context(project_path: Path) -> ProjectContext:
    game = await load_game_metadata(project_path / "metadata" / "game.json")
    characters = await load_character_metadata(project_path / "metadata" / "characters.jsonl")
    # ... load other metadata
    return ProjectContext(game=game, characters=characters, ...)

# ❌ Bad: Blocking synchronous I/O
def load_project_context(project_path: Path) -> ProjectContext:
    with open(project_path / "metadata" / "game.json") as f:
        game = json.load(f)  # Blocks event loop!
```

**Benefits**:
- Concurrent loading of multiple files
- Non-blocking for agent LLM calls
- Scales better with large projects

### Validation at Load Time

Pydantic validation happens in loaders, not at model creation:

```python
async def load_character_metadata(path: Path) -> list[CharacterMetadata]:
    """Load characters.jsonl with validation.

    Raises:
        ValidationError: If any entry has invalid schema.
    """
    entries = await _read_jsonl(path)
    return [CharacterMetadata.model_validate(entry) for entry in entries]
```

**Why**: Validation errors surface immediately when loading data, not later during processing.

---

## Testing Guidelines

### Unit Tests

Test models with valid/invalid data:

```python
def test_character_metadata_valid():
    char = CharacterMetadata(
        id="aya",
        name_src="綾",
        name_src_origin="human",
        name_tgt="Aya",
        name_tgt_origin="human"
    )
    assert char.id == "aya"
    assert char.name_src_origin == "human"


def test_character_metadata_extra_fields():
    char = CharacterMetadata(
        id="aya",
        name_src="綾",
        voice_actor="田中さん"  # Custom field
    )
    assert char.voice_actor == "田中さん"  # extra="allow"
```

### Integration Tests

Test loaders with fixture files:

```python
@pytest.mark.asyncio
async def test_load_characters():
    chars = await load_character_metadata(
        Path("examples/tiny_vn/metadata/characters.jsonl")
    )
    assert len(chars) == 3
    assert chars[0].id == "mc"
```

---

## Best Practices

### DO

- ✅ Use `Field(..., description="...")` for all model fields
- ✅ Include examples in field definitions
- ✅ Use `orjson` for JSON parsing (faster than stdlib)
- ✅ Use `anyio` for async file operations
- ✅ Validate data at load time with Pydantic
- ✅ Keep models simple—no business logic in model classes
- ✅ Document provenance fields clearly

### DON'T

- ❌ Don't add business logic to models (keep them pure data)
- ❌ Don't use blocking I/O (`open()`, `json.load()`)
- ❌ Don't skip validation—always use `model_validate()`
- ❌ Don't modify custom fields in models—they're read-only for agents
- ❌ Don't add `*_origin` fields for identifiers or structural data

---

## Common Patterns

### Loading Project Context

```python
from rentl_core.context import load_project_context

async def main():
    context = await load_project_context(Path("path/to/game_project"))

    # Access metadata
    char = context.get_character("aya")
    scene = context.get_scene("scene_c_00")

    # Load scene lines
    lines = await context.load_scene_lines("scene_c_00")

    # Update metadata with provenance
    char.notes = "Updated bio"
    char.notes_origin = "agent:character_detailer:2024-11-22"
    await context.save_characters()
```

### Adding New Metadata Types

1. Create Pydantic model in `model/`
2. Add `*_origin` fields for trackable content
3. Create async loader in `io/loader.py`
4. Add to `ProjectContext` model
5. Update `load_project_context()` to load it
6. Add save method if needed
7. Document in [SCHEMAS.md](../../SCHEMAS.md)

---

## Dependencies

**Core**:
- `pydantic` (v2+): Data validation and settings
- `pydantic-settings`: Environment variable loading
- `orjson`: Fast JSON parsing
- `anyio`: Async file operations

**No agent dependencies**: `rentl-core` should not depend on `rentl-agents` or `rentl-pipelines`.

---

## Summary

`rentl-core` provides:
- Type-safe data models with provenance tracking
- Fast async I/O for all metadata formats
- Clean separation from business logic (agents/pipelines)
- Foundation for the entire rentl ecosystem

See [SCHEMAS.md](../../SCHEMAS.md) for complete data format specifications.
