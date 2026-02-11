# CLI Help Docstring Gating

Use `\f` (form-feed) to prevent Typer from rendering internal docstring sections.

```python
def run_pipeline():
    """Run the full localization pipeline.
    
    \f
    Raises:
        ConfigError: If config is invalid
        ConnectionError: If endpoint unreachable
    """
```

- `\f` stops Typer's docstring parser
- User sees only the description before `\f`
- Internal sections (Raises, Returns, Args) stay in code but hidden from help
