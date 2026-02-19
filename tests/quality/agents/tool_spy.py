"""Tool call instrumentation for quality evals."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from rentl_agents.tools.game_info import GameInfoTool, ProjectContext
from rentl_agents.tools.legacy import (
    ContextLookupTool,
    GlossarySearchTool,
    StyleGuideLookupTool,
)
from rentl_agents.tools.registry import ToolRegistry
from rentl_schemas.phases import ContextNote, GlossaryTerm, SceneSummary
from rentl_schemas.primitives import JsonValue
from tests.quality.agents.eval_types import ToolCallRecord


class ToolCallRecorder(BaseModel):
    """Collects tool call inputs and outputs."""

    model_config = ConfigDict(extra="forbid")

    calls: list[ToolCallRecord] = Field(
        default_factory=list, description="Recorded tool call entries"
    )

    def record(
        self,
        tool_name: str,
        args: dict[str, JsonValue],
        result: dict[str, JsonValue],
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


class InstrumentedGameInfoTool:
    """Wrapper for GameInfoTool call recording."""

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

    def execute(self, **kwargs: JsonValue) -> dict[str, JsonValue]:
        """Execute tool and record the call.

        Returns:
            Tool result payload.
        """
        result = self._tool.execute(**kwargs)
        args: dict[str, JsonValue] = dict(kwargs)
        self._recorder.record(self._tool.name, args, result)
        return result


class InstrumentedContextLookupTool:
    """Wrapper for ContextLookupTool call recording."""

    def __init__(
        self,
        tool: ContextLookupTool,
        recorder: ToolCallRecorder,
    ) -> None:
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

    def execute(self, **kwargs: JsonValue) -> dict[str, JsonValue]:
        """Execute tool and record the call.

        Returns:
            Tool result payload.
        """
        args: dict[str, JsonValue] = dict(kwargs)
        result = self._tool.execute(args)
        self._recorder.record(self._tool.name, args, result)
        return result


class InstrumentedGlossarySearchTool:
    """Wrapper for GlossarySearchTool call recording."""

    def __init__(
        self,
        tool: GlossarySearchTool,
        recorder: ToolCallRecorder,
    ) -> None:
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

    def execute(self, **kwargs: JsonValue) -> dict[str, JsonValue]:
        """Execute tool and record the call.

        Returns:
            Tool result payload.
        """
        args: dict[str, JsonValue] = dict(kwargs)
        result = self._tool.execute(args)
        self._recorder.record(self._tool.name, args, result)
        return result


class InstrumentedStyleGuideLookupTool:
    """Wrapper for StyleGuideLookupTool call recording."""

    def __init__(
        self,
        tool: StyleGuideLookupTool,
        recorder: ToolCallRecorder,
    ) -> None:
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

    def execute(self, **kwargs: JsonValue) -> dict[str, JsonValue]:
        """Execute tool and record the call.

        Returns:
            Tool result payload.
        """
        args: dict[str, JsonValue] = dict(kwargs)
        result = self._tool.execute(args)
        self._recorder.record(self._tool.name, args, result)
        return result


# Keep InstrumentedTool as an alias for backward compatibility
InstrumentedTool = InstrumentedGameInfoTool


def build_tool_registry(
    recorder: ToolCallRecorder,
    project_context: ProjectContext | None = None,
    scene_summaries: list[SceneSummary] | None = None,
    context_notes: list[ContextNote] | None = None,
    glossary_terms: list[GlossaryTerm] | None = None,
    style_guide_content: str = "",
) -> ToolRegistry:
    """Create a tool registry with instrumented tools.

    Args:
        recorder: Recorder to collect tool calls.
        project_context: Project context for the game info tool.
        scene_summaries: Scene summaries for context lookup.
        context_notes: Context notes for context lookup.
        glossary_terms: Glossary terms for search.
        style_guide_content: Style guide content for lookup.

    Returns:
        ToolRegistry with instrumented tools registered.
    """
    registry = ToolRegistry()
    registry.register(InstrumentedGameInfoTool(GameInfoTool(project_context), recorder))
    registry.register(
        InstrumentedContextLookupTool(
            ContextLookupTool(scene_summaries, context_notes), recorder
        )
    )
    registry.register(
        InstrumentedGlossarySearchTool(GlossarySearchTool(glossary_terms), recorder)
    )
    registry.register(
        InstrumentedStyleGuideLookupTool(
            StyleGuideLookupTool(style_guide_content), recorder
        )
    )
    return registry
