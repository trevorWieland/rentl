# Copy-pasteable Examples

All command examples in documentation must be executable without modification.

```bash
# Good: use dynamic path from rentl status
uv run rentl export --input "$(uv run rentl status --json | jq -r '.latest_run.output_dir')/edited_lines.jsonl" --output translations.csv --format csv

# Also good: concrete example path with realistic run ID
uv run rentl export --input out/run-a1b2c3/edited_lines.jsonl --output translations.csv --format csv

# Bad: placeholder path
uv run rentl export --input out/REPLACE_WITH_RUN_ID/edited_lines.jsonl --output translations.csv --format csv
```

- No `<placeholder>` paths or arguments
- Use real, generated paths from actual workflow (e.g., from `rentl status --json`)
- Exception: secrets the user must provide (API keys) may use `your_key_here`
