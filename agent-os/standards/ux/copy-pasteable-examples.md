# Copy-pasteable Examples

All command examples in documentation must be executable without modification.

```bash
# Good: complete path
uv run rentl export --input out/run-001/edited_lines.jsonl --output translations.csv --format csv

# Bad: placeholder path
uv run rentl export --input <translated-lines.jsonl> --output translations.csv --format csv
```

- No `<placeholder>` paths or arguments
- Use real, generated paths from actual workflow (e.g., from `rentl status --json`)
- Exception: secrets the user must provide (API keys) may use `your_key_here`
