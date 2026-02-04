# Required Tool Calls Gating

If an output depends on a tool call, gate output tools using `prepare_output_tools`.

```python
async def prepare_output_tools(ctx, output_tools):
    if not tool_called(ctx.messages, "get_game_info"):
        return []
    return output_tools

agent = Agent(..., prepare_output_tools=prepare_output_tools, end_strategy="exhaustive")
```

- Use `end_strategy="exhaustive"` when tool calls must still run even if an output tool is returned.
- Gating is required whenever a tool call is required for correctness.

Why
- Output tools are separate from function tools; without gating, a model can return output without calling required tools. See: https://ai.pydantic.dev/output/#tool-output and https://ai.pydantic.dev/tools-advanced/
