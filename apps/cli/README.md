# rentl-cli: Command-Line Interface

Typer-based CLI for running rentl translation workflows.

---

## Purpose

`rentl-cli` provides user-facing commands to:

- Initialize new game projects (`rentl init`)
- Validate project structure and metadata (`rentl validate`)
- Run translation pipelines (`rentl context`, `rentl translate`, `rentl edit`)
- Manage project configuration

**Target users**: Translators and localization teams working on visual novels.

---

## Scope

### In Scope

- Typer command definitions
- Project path resolution and validation
- Pipeline invocation (delegates to `rentl-pipelines`)
- Progress reporting and user feedback
- Error handling and user-friendly messages
- Flag/option parsing (`--overwrite`, `--verbose`, etc.)

### Out of Scope

- Pipeline orchestration logic (belongs in `rentl-pipelines`)
- Agent implementations (belongs in `rentl-agents`)
- Data models and I/O (belongs in `rentl-core`)

---

## Command Structure

### Available Commands (v1.0)

```bash
rentl init [PROJECT_NAME]           # Create new project from template
rentl validate                      # Validate metadata and scenes
rentl context                       # Run Context Builder phase
rentl translate                     # Run Translator phase
rentl edit                          # Run Editor phase
```

### Common Flags

All commands support:

```bash
--project-path PATH    # Path to game project (default: current directory)
--verbose              # Enable detailed logging
--help                 # Show command help
```

Phase-specific flags:

```bash
--overwrite            # Allow overwriting existing data (context phase)
--scene SCENE_ID       # Process specific scene only
```

---

## Design Patterns

### Typer Application

Main CLI app in `main.py`:

```python
import typer
from typing_extensions import Annotated

app = typer.Typer(
    name="rentl",
    help="Multi-agent translation pipeline for visual novels",
    no_args_is_help=True
)

@app.command()
def validate(
    project_path: Annotated[Path, typer.Option(help="Path to game project")] = Path("."),
    verbose: Annotated[bool, typer.Option(help="Enable verbose logging")] = False
):
    """Validate metadata and scene files."""
    if verbose:
        setup_logging(level="DEBUG")

    context = asyncio.run(load_project_context(project_path))
    errors = validate_project(context)

    if errors:
        for error in errors:
            typer.secho(f"✗ {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    else:
        typer.secho("✓ Project validation passed", fg=typer.colors.GREEN)
```

**Benefits**:
- Type-safe argument parsing
- Automatic `--help` generation
- Clear error messages

### Async Command Wrapper

Typer commands are synchronous, but pipelines are async:

```python
def context(
    project_path: Path = Path("."),
    overwrite: bool = False,
    scene: str | None = None,
    verbose: bool = False
):
    """Run Context Builder phase."""
    if verbose:
        setup_logging(level="DEBUG")

    # Wrap async pipeline in sync context
    asyncio.run(_run_context_async(project_path, overwrite, scene))


async def _run_context_async(
    project_path: Path,
    overwrite: bool,
    scene: str | None
):
    """Async implementation of context command."""
    context = await load_project_context(project_path)

    if scene:
        # Single scene
        result = await run_context_builder(context, scene, overwrite)
        typer.echo(f"✓ Processed {scene}: {result.summary}")
    else:
        # All scenes
        results = await run_context_pipeline(
            context,
            list(context.scenes.keys()),
            overwrite,
            progress_callback=_print_progress
        )
        typer.echo(f"✓ Processed {len(results)} scenes")
```

### Progress Reporting

Show progress for long-running operations:

```python
def _print_progress(scene_id: str, current: int, total: int):
    """Progress callback for pipeline."""
    percentage = (current / total) * 100
    typer.echo(
        f"[{current}/{total}] ({percentage:.0f}%) Processing {scene_id}...",
        nl=False
    )
    typer.echo("\r", nl=False)  # Clear line for next update


# Final newline after completion
typer.echo()
```

### Error Handling

Provide helpful error messages:

```python
try:
    context = asyncio.run(load_project_context(project_path))
except FileNotFoundError as e:
    typer.secho(
        f"✗ Error: {e}\n"
        f"  Make sure you're in a rentl project directory or use --project-path",
        fg=typer.colors.RED
    )
    raise typer.Exit(code=1)
except ValidationError as e:
    typer.secho(
        f"✗ Validation error in metadata:\n{e}",
        fg=typer.colors.RED
    )
    raise typer.Exit(code=1)
```

**Principles**:
- Catch specific exceptions
- Provide actionable error messages
- Use colored output (red for errors, green for success)
- Exit with non-zero code on failure

---

## Best Practices

### DO

- ✅ Use Typer's type annotations for arguments/options
- ✅ Provide clear, concise help text for all commands
- ✅ Wrap async pipelines in `asyncio.run()`
- ✅ Show progress for long-running operations
- ✅ Use colored output for success/error messages
- ✅ Validate inputs early (project path exists, scene ID valid, etc.)
- ✅ Exit with appropriate codes (0 = success, 1 = error)

### DON'T

- ❌ Don't implement pipeline logic in CLI commands
- ❌ Don't print raw exceptions—format them for users
- ❌ Don't block without progress indication
- ❌ Don't use generic error messages ("Error occurred")
- ❌ Don't mix sync and async incorrectly (use `asyncio.run()`)

---

## Command Examples

### validate

```bash
# Validate current directory
rentl validate

# Validate specific project
rentl validate --project-path ~/games/my_vn

# Verbose output
rentl validate --verbose
```

**Output**:
```
Checking metadata files...
✓ game.json is valid
✓ characters.jsonl is valid (3 entries)
✓ scenes.jsonl is valid (12 entries)

Checking referential integrity...
✓ All routes reference valid scenes
✓ All scenes belong to valid routes

✓ Project validation passed
```

### context

```bash
# Run context builder on all scenes
rentl context

# Process specific scene
rentl context --scene scene_c_00

# Allow overwriting existing summaries
rentl context --overwrite

# Verbose logging
rentl context --verbose
```

**Output**:
```
[1/12] (8%) Processing scene_c_00...
[2/12] (17%) Processing scene_a_00...
...
[12/12] (100%) Processing scene_r_01...

✓ Processed 12 scenes
  - 8 scenes enriched
  - 4 scenes skipped (already complete, use --overwrite to update)
```

### translate

```bash
# Translate all scenes
rentl translate

# Translate specific scene
rentl translate --scene scene_c_00

# Use specific LLM model
rentl translate --model gpt-4o
```

**Output**:
```
[1/12] (8%) Translating scene_c_00... (42 lines)
[2/12] (17%) Translating scene_a_00... (38 lines)
...

✓ Translated 12 scenes (478 total lines)
  Outputs saved to: output/translations/
```

### edit

```bash
# Run editor on all translated scenes
rentl edit

# Check specific scene
rentl edit --scene scene_c_00

# Run specific QA checks only
rentl edit --checks style,consistency
```

**Output**:
```
Running QA checks...
[1/12] scene_c_00
  ✓ Style guide compliance
  ✓ Pronoun consistency
  ✗ Line length (2 lines exceed 42 chars)

[2/12] scene_a_00
  ✓ All checks passed

...

✓ Completed QA checks
  - 10 scenes passed all checks
  - 2 scenes have warnings
  - 0 scenes failed

See output/reports/ for detailed results
```

---

## Testing

### Unit Tests

Test command parsing and validation:

```python
from typer.testing import CliRunner
from rentl_cli.main import app

runner = CliRunner()

def test_validate_command():
    result = runner.invoke(app, ["validate", "--project-path", "examples/tiny_vn"])
    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()


def test_validate_invalid_path():
    result = runner.invoke(app, ["validate", "--project-path", "/nonexistent"])
    assert result.exit_code == 1
    assert "error" in result.stdout.lower()
```

### Integration Tests

Test full command workflows:

```python
def test_full_workflow():
    runner = CliRunner()

    # Validate
    result = runner.invoke(app, ["validate", "--project-path", "examples/tiny_vn"])
    assert result.exit_code == 0

    # Context
    result = runner.invoke(app, ["context", "--project-path", "examples/tiny_vn"])
    assert result.exit_code == 0
    assert "processed" in result.stdout.lower()
```

---

## Future Enhancements

### Interactive Mode (v1.1+)

```bash
rentl interactive  # Start interactive session
> validate
> context --scene scene_c_00
> translate
```

### Configuration Management (v1.1+)

```bash
rentl config set llm.model gpt-4o
rentl config get llm.model
rentl config list
```

### Diff and Review (v1.1+)

```bash
rentl diff scene_c_00           # Show changes since last commit
rentl review scene_c_00         # Launch interactive review
```

---

## Dependencies

**Required**:
- `typer`: CLI framework
- `rich`: Colored output and formatting (optional but recommended)
- `rentl-core`: Data models and I/O
- `rentl-pipelines`: Pipeline orchestration
- `rentl-templates`: For `init` command

**Python**: 3.13+

---

## Summary

`rentl-cli` provides:
- User-friendly commands for translation workflows
- Clear progress reporting and error messages
- Type-safe argument parsing with Typer
- Wrapper around async pipelines

**Design principle**: CLI handles user interaction; pipelines handle business logic.

See [AGENTS.md](../../AGENTS.md) for coding guidelines and [README.md](../../README.md) for user documentation.
