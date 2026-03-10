# Config Path Resolution

All paths in `rentl.toml` resolve relative to the config file's parent directory, not the current working directory.

## Resolution chain

1. `.env` — loaded from `config_path.parent / ".env"`
2. `workspace_dir` — if relative, resolved as `config_path.parent / workspace_dir`
3. `input_path`, `output_dir`, `logs_dir` — resolved relative to `workspace_dir`
4. `agents_dir`, `prompts_dir` — must be within `workspace_dir`

## Practical guidance

- Keep config files within the project repository (e.g., `rentl.toml` at repo root)
- Use `workspace_dir = "."` when the config is at the repo root
- If config must live elsewhere, use absolute `workspace_dir` pointing to the repo
- Place `.env` next to the config file, or symlink it there
- All relative paths in `[project.paths]` resolve through `workspace_dir`, not CWD

## Anti-patterns

```toml
# BAD: config in /tmp/ with relative workspace_dir
# File: /tmp/my-run/rentl.toml
[project.paths]
workspace_dir = "."  # resolves to /tmp/my-run/, agents not found

# GOOD: absolute workspace pointing to repo
[project.paths]
workspace_dir = "/home/user/github/rentl"
```

## Why

Walk-spec demo hit 4+ config failures from agents placing configs in `/tmp/` with `workspace_dir = "."`. The CLI resolves `workspace_dir` relative to `config_path.parent` (`main.py:2124-2127`), so configs outside the repo can't find agents, prompts, or input files.
