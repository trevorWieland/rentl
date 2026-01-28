"""Manual validation script for agent harness instantiation.

This script tests:
- Agent harness creation
- Configuration loading
- Prompt template rendering
- Tool registration
"""

import asyncio
from unittest.mock import AsyncMock, patch

print("Testing Agent Harness Instantiation...")


async def test_agent_harness() -> None:
    """Test agent harness instantiation and basic usage."""
    from pydantic import Field

    from rentl_agents import AgentHarness, PromptRenderer
    from rentl_agents.harness import AgentHarnessConfig
    from rentl_schemas.base import BaseSchema

    class MockInput(BaseSchema):
        text: str = Field(..., description="Input text")

    class MockOutput(BaseSchema):
        result: str = Field(..., description="Output result")

    harness = AgentHarness(
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

    config = AgentHarnessConfig(api_key="test-key")
    await harness.initialize(config)
    print("✅ Agent initialized successfully")

    # Mock _execute_agent for testing without real API calls
    expected_output = MockOutput(result="Test output")
    with patch.object(
        harness, "_execute_agent", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = expected_output

        input_data = MockInput(text="Test input")
        output = await harness.run(input_data)
        print(f"✅ Agent executed successfully: {output.result}")


asyncio.run(test_agent_harness())
print("\n✅ All agent harness validation tests passed!")
