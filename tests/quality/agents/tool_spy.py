"""Tool call instrumentation for quality evals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rentl_agents.tools.game_info import GameInfoTool, ProjectContext
from rentl_agents.tools.registry import ToolRegistry
from tests.quality.agents.eval_types import ToolCallRecord


@dataclass
class ToolCallRecorder:
    """Collects tool call inputs and outputs."""

    calls: list[ToolCallRecord] = field(default_factory=list)

    def record(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Record a tool call.

        Args:
            tool_name: Tool identifier.
            args: Tool input arguments.
            result: Tool output payload.
        """
        self.calls.append(
            ToolCallRecord(
                tool_name=tool_name,
                args=dict(args),
                result=dict(result),
            )
        )


class InstrumentedTool:
    """Wrapper for tool call recording."""

    def __init__(self, tool: GameInfoTool, recorder: ToolCallRecorder) -> None:
        """Initialize the instrumented tool wrapper.

        Args:
            tool: Tool implementation to wrap.
            recorder: Recorder to capture calls.
        """
        self._tool = tool
        self._recorder = recorder

    @property
    def name(self) -> str:
        """Tool identifier."""
        return self._tool.name

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        return self._tool.description

    def execute(self, **kwargs: object) -> dict[str, Any]:
        """Execute tool and record the call.

        Returns:
            Tool result payload.
        """
        result = self._tool.execute(**kwargs)
        self._recorder.record(self._tool.name, kwargs, result)
        return result


def build_tool_registry(
    recorder: ToolCallRecorder,
    project_context: ProjectContext | None = None,
) -> ToolRegistry:
    """Create a tool registry with instrumented tools.

    Args:
        recorder: Recorder to collect tool calls.
        project_context: Project context for the game info tool.

    Returns:
        ToolRegistry with instrumented tools registered.
    """
    registry = ToolRegistry()
    registry.register(InstrumentedTool(GameInfoTool(project_context), recorder))
    return registry
