# rentl-templates: Project Scaffolding

Copier templates for creating per-game translation projects.

---

## Purpose

`rentl-templates` provides Copier templates that scaffold new game translation projects with:

- Standard directory structure (`metadata/`, `input/`, `output/`)
- Pre-configured metadata files with sensible defaults
- Example context documents and style guide
- Project configuration (`rentl.project.toml`)

**Goal**: One `rentl init` command creates a complete, git-ready project for a new game.

---

## Scope

### In Scope

- Copier template definition (`copier.yml`)
- Template directory structure with placeholders
- Default metadata file templates (empty but valid)
- Example style guide and context docs
- Project configuration template
- Git-friendly defaults (`.gitignore`, etc.)

### Out of Scope

- Actual game data (users populate `input/scenes/` themselves)
- Agent logic (belongs in `rentl-agents`)
- CLI commands (belongs in `rentl-cli`)

---

## Template Structure

```
libs/templates/src/rentl_templates/copier/
  copier.yml                          # Copier configuration
  {{project_slug}}/                   # Template directory (variables in {{}})
    .gitignore
    rentl.project.toml                # Project config template
    metadata/
      game.json.jinja                 # Game metadata template
      characters.jsonl                # Empty (users fill manually or via agents)
      glossary.jsonl                  # Empty
      locations.jsonl                 # Empty
      routes.jsonl                    # Empty
      scenes.jsonl                    # Empty
      style_guide.md                  # Example style guide
      context_docs/
        .gitkeep                      # Ensure directory exists
    input/
      scenes/
        .gitkeep                      # Users add scene files here
    output/
      translations/
        .gitkeep
      reports/
        .gitkeep
```

---

## Copier Configuration

### copier.yml

Defines template variables and rendering:

```yaml
_subdirectory: "{{project_slug}}"

# Questions asked during `rentl init`
project_name:
  type: str
  help: "Game title (human-readable)"
  default: "My Visual Novel"

project_slug:
  type: str
  help: "Project directory name (lowercase, underscores)"
  default: "{{ project_name|lower|replace(' ', '_') }}"

source_lang:
  type: str
  help: "Source language (ISO 639-3 code)"
  default: "jpn"

target_lang:
  type: str
  help: "Target language (ISO 639-3 code)"
  default: "eng"

description:
  type: str
  help: "Short project description"
  default: ""
```

### Template Variables

Variables can be used in template files with Jinja2 syntax:

**game.json.jinja**:
```json
{
  "title": "{{ project_name }}",
  "title_origin": "human",
  "description": "{{ description }}",
  "description_origin": "human",
  "source_lang": "{{ source_lang }}",
  "target_lang": "{{ target_lang }}",
  "genres": [],
  "genres_origin": null,
  "synopsis": null,
  "synopsis_origin": null,
  "timeline": [],
  "timeline_origin": null,
  "ui": {
    "max_line_length": null,
    "allow_word_wrap": true,
    "charset": "unicode"
  }
}
```

---

## Design Principles

### Valid from the Start

All template files must be **valid** according to [SCHEMAS.md](../../SCHEMAS.md):

- Empty JSONL files are valid (zero entries)
- `game.json` has all required fields with sensible defaults
- Origin fields are set to `null` for empty optional fields

**Why**: Users can run `rentl validate` immediately after `rentl init` without errors.

### Git-Friendly

Templates include:

- `.gitignore` for common exclusions (`.env`, `*.pyc`, etc.)
- `.gitkeep` files in empty directories
- README.md explaining project structure

**Why**: Projects are ready for `git init` and version control from day one.

### Minimal but Complete

Templates provide **structure**, not content:

- Metadata files are empty but valid (users fill via agents or manually)
- Style guide has examples but users should customize
- No fake/placeholder game data

**Why**: Users start with a clean slate tailored to their specific game.

### Provenance-Ready

All content fields in templates include corresponding `*_origin` fields:

```jsonl
{"id": "mc", "name_src": "", "name_src_origin": null, "name_tgt": null, "name_tgt_origin": null}
```

**Why**: Schema is ready for agents to fill in data with provenance tracking.

---

## Usage

### Creating a New Project

```bash
# From rentl repo root
rentl init my_vn_project

# Answer prompts:
# Game title: My Visual Novel
# Project slug: my_vn_project
# Source language: jpn
# Target language: eng
# Description: A heartwarming story about friendship
```

**Result**:

```
my_vn_project/
  .gitignore
  rentl.project.toml
  metadata/
    game.json              # Populated with answers
    characters.jsonl       # Empty but valid
    glossary.jsonl         # Empty
    ...
  input/
    scenes/                # Empty, ready for user's scene files
  output/
    translations/          # Empty, will be populated by agents
    reports/
```

### Customizing Templates

To add a new template file:

1. Create file in `{{project_slug}}/` directory
2. Use Jinja2 syntax for variables: `{{ project_name }}`
3. Ensure file is valid according to its schema
4. Add `.gitkeep` if it's an empty directory
5. Test with `copier copy libs/templates/copier test_project`

---

## Best Practices

### DO

- ✅ Keep templates minimal and valid
- ✅ Use Jinja2 variables for user-provided values
- ✅ Include helpful comments in generated files
- ✅ Provide example content in style_guide.md
- ✅ Set `*_origin` fields to `null` for empty content
- ✅ Include `.gitignore` and `.gitkeep` files

### DON'T

- ❌ Don't include fake game data (users provide real data)
- ❌ Don't make templates too opinionated (keep flexible)
- ❌ Don't skip `*_origin` fields (breaks provenance tracking)
- ❌ Don't generate invalid files (must pass `rentl validate`)
- ❌ Don't hardcode values that should be user-configurable

---

## Testing Templates

### Manual Testing

```bash
# From rentl repo root
copier copy libs/templates/copier test_project

# Check generated project
cd test_project
uv run python -m rentl_cli.main validate
```

### Automated Testing

```python
import subprocess
from pathlib import Path

def test_template_generation():
    # Generate project with default values
    subprocess.run([
        "copier", "copy",
        "--data", "project_name=Test VN",
        "--data", "project_slug=test_vn",
        "libs/templates/copier",
        "tmp/test_vn"
    ])

    # Validate generated structure
    project_path = Path("tmp/test_vn")
    assert (project_path / "metadata" / "game.json").exists()
    assert (project_path / "input" / "scenes").is_dir()

    # Validate files
    result = subprocess.run(
        ["rentl", "validate", "--project-path", "tmp/test_vn"],
        capture_output=True
    )
    assert result.returncode == 0
```

---

## Common Patterns

### Adding a New Metadata File Template

1. **Create template file**:
   ```
   {{project_slug}}/metadata/items.jsonl
   ```

2. **Make it valid but empty**:
   ```jsonl
   # Empty file (valid JSONL = zero entries)
   ```

3. **Update data models** in `rentl-core` to match schema

4. **Document schema** in [SCHEMAS.md](../../SCHEMAS.md)

5. **Add loader** in `rentl-core/io/loader.py`

### Customizing Project Config

Add questions to `copier.yml`:

```yaml
max_line_length:
  type: int
  help: "Maximum line length for game engine"
  default: null

allow_word_wrap:
  type: bool
  help: "Does your engine support word wrapping?"
  default: true
```

Use in template:

```toml
# rentl.project.toml.jinja
[ui]
max_line_length = {{ max_line_length or "null" }}
allow_word_wrap = {{ "true" if allow_word_wrap else "false" }}
```

---

## Future Enhancements (v1.1+)

### Multi-Language Support

Support templates for different language pairs:

```yaml
template_variant:
  type: str
  help: "Template variant"
  choices:
    - "jp_to_en"
    - "zh_to_en"
    - "ko_to_en"
```

### Engine-Specific Templates

Provide templates optimized for specific engines:

```yaml
game_engine:
  type: str
  help: "Game engine"
  choices:
    - "renpy"
    - "kirikiri"
    - "rpgmaker"
```

### Pre-Filled Examples

Option to include sample data for testing:

```yaml
include_examples:
  type: bool
  help: "Include example scenes for testing?"
  default: false
```

---

## Dependencies

**Required**:
- `copier`: Template engine

**No runtime dependencies**: Templates are static files, no Python deps needed.

---

## Summary

`rentl-templates` provides:
- Clean, valid project scaffolding via Copier
- Git-ready structure with sensible defaults
- Provenance-ready metadata files
- One-command project initialization

**Goal**: Users run `rentl init` and immediately have a working project structure ready for their game data.

See [SCHEMAS.md](../../SCHEMAS.md) for metadata file specifications.
