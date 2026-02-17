# Frictionless by Default

Guided CLI + safe defaults make first run feel effortless. Users should succeed without reading docs or expert knowledge.

```python
# ✓ Good: Guided setup with safe defaults
async def init_command(project_dir: str) -> None:
    """Initialize project with guided setup."""
    # Step 1: Detect game type (with default)
    game_type = await detect_game_type(project_dir)
    if game_type is None:
        game_type = await ask_user(
            "What game engine are you translating?",
            options=["RPG Maker", "Ren'Py", "Kirikiri", "Other"],
            default="Ren'Py"  # Safe default
        )
    
    # Step 2: Suggest config with safe defaults
    config = generate_config_with_defaults(game_type)
    print(f"Generated config for {game_type} with:")
    print(f"  - Model: {config.model} (safe default)")
    print(f"  - Language: {config.target_language} (detect from files or ask)")
    
    # Step 3: Validate before proceeding
    if not await validate_config(config):
        print("Config needs adjustment. Let's fix:")
        config = await guided_config_fix(config)
    
    save_config(config)
    print("✓ Project initialized. Run 'rentl run-pipeline' to start.")

# ✓ Good: CLI with defaults and guided flow
$ rentl init
Detected game engine: Ren'Py
Suggested config:
  - Model: gpt-5-nano (recommended for speed/cost)
  - Target language: English (detected from project)
  - Source files: ./src/scripts.rpy (auto-detected)

Accept defaults? [Y/n]: Y
✓ Config saved to rentl.toml

# ✗ Bad: Manual configuration without guidance
async def init_command(project_dir: str) -> None:
    """Initialize project - manual configuration required."""
    print("Create rentl.toml manually. See docs for all options.")
    print("Required fields: model, api_key, source, target, phases...")
    # User must read docs to understand all required fields
    # No defaults, no guidance, no validation
    # High friction for first-time users
```

**Guided setup requirements:**
- **Interactive init:** Ask questions with sensible defaults when auto-detection fails
- **Auto-detection:** Detect game engine, source files, language from project structure
- **Safe defaults:** Provide defaults that work for most common use cases
- **Validation:** Validate config before accepting; fix issues interactively
- **Next steps:** Always tell user what to do next

**Default behavior:**
- **Model:** Recommend cost-effective default (e.g., gpt-5-nano for translation speed)
- **Language:** Detect from project or files; default to English if unclear
- **Source paths:** Auto-detect common patterns (scripts/, src/, data/)
- **Phase selection:** Enable all phases by default; let user opt-out if needed
- **Concurrency:** Default to safe parallelism (e.g., 3-5 concurrent requests)

**Configuration flow:**
1. Auto-detect what's possible (game engine, files, language)
2. Ask for missing info with safe defaults pre-filled
3. Show what will be configured before accepting
4. Validate config and fix issues interactively
5. Save and show next steps

**Exceptions (non-standard workflows):**
Only when non-standard workflow requires customization beyond defaults (e.g., custom engine adapters, specialized QA rules), prompt user for configuration but still provide reasonable defaults.

**Why:** First run succeeds without reading docs or expert knowledge; reduces onboarding friction for lightly technical users; creates positive "already?" moment when pipeline works immediately.
