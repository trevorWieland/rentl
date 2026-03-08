# Pydantic-AI Agent for All LLM Calls

All code that calls an LLM must use `pydantic_ai.Agent` with `output_type`. Never hand-roll JSON parsing, text extraction, or response format negotiation.

```python
from pydantic_ai import Agent

class MyOutput(BaseModel):
    field: str = Field(..., description="...")

agent = Agent(model=model, output_type=MyOutput, output_retries=5)
result = await agent.run(prompt, model_settings=settings)
output = result.output  # validated MyOutput instance
```

- Define output as a Pydantic `BaseModel` with `Field(description=...)` on every field
- Use `output_retries` for automatic retry on validation failure
- Use `model_settings=ModelSettings(...)` for temperature, max_tokens, etc.
- Use pydantic-ai model classes (`OpenRouterModel`, `OpenAIChatModel`) for endpoint config
- Never use `LlmRuntimeProtocol` or `LlmPromptRequest` for new LLM calls

## Anti-patterns

```python
# BAD: hand-rolled JSON extraction
response = await llm.call(prompt)
data = json.loads(response.text)  # fragile
result = MyOutput(**data)  # no retry on parse failure

# BAD: fallback parsing chains
def _extract_json(text):
    # try markdown fences, then regex, then raw parse...
    # This is what pydantic-ai eliminates
```

## Why

Benchmark judge hand-rolled JSON parsing led to 419 lines of extraction/fallback code and 5+ failed audit rounds. Rewriting to `Agent[None, JudgeOutput]` deleted all of it. Pydantic-ai handles provider-specific structured output negotiation (response_format, tool-based output, schema enforcement) across all model families.
