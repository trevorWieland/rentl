"""Tool system for agent capabilities."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from rentl_schemas.base import BaseSchema
from rentl_schemas.phases import (
    ContextNote,
    GlossaryTerm,
    SceneSummary,
)
from rentl_schemas.primitives import LineId, SceneId


@runtime_checkable
class AgentToolProtocol(Protocol):
    """Protocol defining tool contract for agents.

    Tools provide agent capabilities beyond text generation.
    """

    @property
    def get_name(self) -> str:
        """Tool identifier."""
        raise NotImplementedError

    @property
    def get_description(self) -> str:
        """Tool description for LLM."""
        raise NotImplementedError

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool.

        Args:
            input_data: Tool input dictionary.

        Returns:
            Tool output dictionary.

        Raises:
            RuntimeError: If tool execution fails.
        """
        raise NotImplementedError

    @property
    def get_schema(self) -> dict[str, Any]:
        """Tool input/output schemas.

        Returns:
            Schema dictionary.
        """
        raise NotImplementedError

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        raise NotImplementedError

    @property
    def schema(self) -> dict[str, Any]:
        """Tool input/output schemas.

        Returns:
            Schema dictionary.
        """
        raise NotImplementedError


class ToolInput(BaseSchema):
    """Base schema for tool inputs."""

    tool_name: str = Field(..., min_length=1, description="Tool identifier")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )


class ToolOutput(BaseSchema):
    """Base schema for tool outputs."""

    tool_name: str = Field(..., min_length=1, description="Tool identifier")
    result: dict[str, Any] = Field(
        default_factory=dict, description="Tool execution result"
    )
    success: bool = Field(..., description="Whether tool execution succeeded")
    error: str | None = Field(None, description="Error message if failed")


class ContextLookupToolInput(BaseSchema):
    """Input for context lookup tool."""

    scene_id: SceneId | None = Field(None, description="Scene identifier to lookup")
    line_id: LineId | None = Field(None, description="Line identifier to lookup")


class ContextLookupToolOutput(BaseSchema):
    """Output from context lookup tool."""

    scene_summaries: list[SceneSummary] = Field(
        default_factory=list, description="Scene summaries"
    )
    context_notes: list[ContextNote] = Field(
        default_factory=list, description="Context notes"
    )


class GlossarySearchToolInput(BaseSchema):
    """Input for glossary search tool."""

    keyword: str = Field(..., min_length=1, description="Keyword to search")
    exact_match: bool = Field(default=False, description="Match exact keyword only")


class GlossarySearchToolOutput(BaseSchema):
    """Output from glossary search tool."""

    terms: list[GlossaryTerm] = Field(
        default_factory=list, description="Matching glossary terms"
    )


class StyleGuideLookupToolInput(BaseSchema):
    """Input for style guide lookup tool."""

    section: str | None = Field(None, description="Section name to lookup")
    keyword: str | None = Field(None, description="Keyword to search in style guide")


class StyleGuideLookupToolOutput(BaseSchema):
    """Output from style guide lookup tool."""

    content: str = Field(..., description="Style guide content")
    section: str | None = Field(None, description="Section name")


class AgentTool:
    """Base agent tool implementation.

    This class provides a common interface for agent tools.
    """

    def __init__(self, name: str, description: str) -> None:
        """Initialize agent tool.

        Args:
            name: Tool identifier.
            description: Tool description for LLM.

        Raises:
            ValueError: If name or description is invalid.
        """
        if not name:
            raise ValueError("Tool name must not be empty")
        if not description:
            raise ValueError("Tool description must not be empty")
        self._name = name
        self._description = description

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool.

        Args:
            input_data: Tool input dictionary.

        Returns:
            Tool output dictionary.
        """
        return {"tool_name": self._name, "result": "success"}

    @property
    def name(self) -> str:
        """Tool identifier."""
        return self._name

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        return self._description

    @property
    def schema(self) -> dict[str, Any]:
        """Tool input/output schemas.

        Returns:
            Schema dictionary.
        """
        return {"input": {}, "output": {}}


class ContextLookupTool(AgentTool):
    """Tool for looking up scene context and notes.

    This tool retrieves:
    - Scene summaries
    - Context notes associated with scenes or lines

    Args:
        scene_summaries: Scene summaries data.
        context_notes: Context notes data.
    """

    def __init__(
        self,
        scene_summaries: list[SceneSummary] | None = None,
        context_notes: list[ContextNote] | None = None,
    ) -> None:
        """Initialize context lookup tool.

        Args:
            scene_summaries: Scene summaries to lookup.
            context_notes: Context notes to lookup.
        """
        super().__init__(
            name="context_lookup",
            description="Lookup scene summaries and context notes",
        )
        self._scene_summaries = scene_summaries or []
        self._context_notes = context_notes or []

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute context lookup.

        Args:
            input_data: Tool input with scene_id or line_id.

        Returns:
            Context lookup output dictionary.

        Raises:
            RuntimeError: If execution fails.
        """
        try:
            parsed_input = ContextLookupToolInput(**input_data)
        except Exception as exc:
            raise RuntimeError(f"Invalid input for context_lookup: {exc}") from exc

        summaries: list[SceneSummary] = []
        notes: list[ContextNote] = []

        if parsed_input.scene_id is not None:
            summaries = [
                s for s in self._scene_summaries if s.scene_id == parsed_input.scene_id
            ]
            notes = [
                n for n in self._context_notes if n.scene_id == parsed_input.scene_id
            ]

        if parsed_input.line_id is not None:
            notes.extend([
                n for n in self._context_notes if n.line_id == parsed_input.line_id
            ])

        output = ContextLookupToolOutput(
            scene_summaries=summaries,
            context_notes=notes,
        )
        return output.model_dump()


class GlossarySearchTool(AgentTool):
    """Tool for searching glossary terms.

    This tool searches glossary by keyword with optional exact matching.

    Args:
        glossary_terms: Glossary terms to search.
    """

    def __init__(self, glossary_terms: list[GlossaryTerm] | None = None) -> None:
        """Initialize glossary search tool.

        Args:
            glossary_terms: Glossary terms to search.
        """
        super().__init__(
            name="glossary_search",
            description="Search glossary terms by keyword",
        )
        self._glossary_terms = glossary_terms or []

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute glossary search.

        Args:
            input_data: Tool input with keyword and exact_match flag.

        Returns:
            Glossary search output dictionary.

        Raises:
            RuntimeError: If execution fails.
        """
        try:
            parsed_input = GlossarySearchToolInput(**input_data)
        except Exception as exc:
            raise RuntimeError(f"Invalid input for glossary_search: {exc}") from exc

        keyword_lower = parsed_input.keyword.lower()
        matching_terms: list[GlossaryTerm] = []

        for term in self._glossary_terms:
            term_text = term.term.lower()

            if parsed_input.exact_match:
                if term_text == keyword_lower:
                    matching_terms.append(term)
            else:
                if keyword_lower in term_text:
                    matching_terms.append(term)

        output = GlossarySearchToolOutput(terms=matching_terms)
        return output.model_dump()


class StyleGuideLookupTool(AgentTool):
    """Tool for looking up style guide content.

    This tool retrieves style guide sections or searches by keyword.

    Args:
        style_guide_content: Full style guide content.
    """

    def __init__(self, style_guide_content: str = "") -> None:
        """Initialize style guide lookup tool.

        Args:
            style_guide_content: Full style guide content.
        """
        super().__init__(
            name="style_guide_lookup",
            description="Lookup style guide content by section or keyword",
        )
        self._style_guide_content = style_guide_content

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute style guide lookup.

        Args:
            input_data: Tool input with section or keyword.

        Returns:
            Style guide lookup output dictionary.

        Raises:
            RuntimeError: If execution fails.
        """
        try:
            parsed_input = StyleGuideLookupToolInput(**input_data)
        except Exception as exc:
            raise RuntimeError(f"Invalid input for style_guide_lookup: {exc}") from exc

        content = self._style_guide_content
        section: str | None = None

        if parsed_input.section:
            section = parsed_input.section
            lines = content.split("\n")
            section_start = -1

            for i, line in enumerate(lines):
                if parsed_input.section.lower() in line.lower():
                    section_start = i
                    break

            if section_start >= 0:
                section_lines: list[str] = []
                for line in lines[section_start + 1 :]:
                    if line.startswith("#") or line.startswith("##"):
                        break
                    section_lines.append(line)
                content = "\n".join(section_lines).strip()

        elif parsed_input.keyword:
            lines = content.split("\n")
            matching_lines = [
                line for line in lines if parsed_input.keyword.lower() in line.lower()
            ]
            content = "\n".join(matching_lines)

        output = StyleGuideLookupToolOutput(
            content=content,
            section=section,
        )
        return output.model_dump()
