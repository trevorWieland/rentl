# Agent Tool Registration

Register tools using `pydantic_ai.Tool` with explicit `name` and `description`.

```python
from pydantic_ai import Tool

registry.register(
    Tool(tool.execute, name=tool.name, description=tool.description, takes_ctx=False)
)
```

- Never pass raw callables (e.g., `tool.execute`) directly to `Agent(..., tools=...)`.
- Prompts must reference the exact tool `name` exposed to the model.

Why
- Pydantic-AI derives tool identity from the function/tool schema; raw callables expose the function name (often `execute`), which breaks prompt/tool alignment. See: https://ai.pydantic.dev/tools/ and https://ai.pydantic.dev/tools-advanced/
