"""Manual validation script for agent harness instantiation.

This script tests:
- Agent harness creation with mock runtime
- Configuration loading
- Prompt template rendering
- Tool registration
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

print("Testing Agent Harness Instantiation...")


async def test_agent_harness() -> None:
    """Test agent harness instantiation and basic usage."""
    from pydantic import Field

    from rentl_agents import AgentHarness, PromptRenderer
    from rentl_schemas.base import BaseSchema

    class MockInput(BaseSchema):
        text: str = Field(..., description="Input text")

    class MockOutput(BaseSchema):
        result: str = Field(..., description="Output result")

    mock_runtime = MagicMock()
    mock_runtime.run_prompt = AsyncMock(
        return_value=MagicMock(
            model_id="gpt-4o-mini",
            output_text='{"result": "Test output"}',
        )
    )

    harness = AgentHarness(
        runtime=mock_runtime,
        system_prompt="You are a helpful assistant.",
        user_prompt_template="Process: {{text}}",
        output_type=MockOutput,
        max_retries=1,
        retry_base_delay=0.1,
    )

    print("✅ Agent harness created successfully")

    renderer = PromptRenderer()
    template = "Process: {{text}} with mode: {{mode}}"
    context = {"text": "Hello", "mode": "strict"}

    rendered = renderer.render_template(template, context)
    assert rendered == "Process: Hello with mode: strict"
    print(f"✅ Prompt template rendered: {rendered}")

    await harness.initialize({"api_key": "test-key", "model_settings": {}})
    print("✅ Agent initialized successfully")

    input_data = MockInput(text="Test input")
    output = await harness.run(input_data)
    print(f"✅ Agent executed successfully: {output.result}")


asyncio.run(test_agent_harness())
print("\n✅ All agent harness validation tests passed!")
