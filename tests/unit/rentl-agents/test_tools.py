"""Unit tests for agent tools."""

from __future__ import annotations

from uuid import uuid7

import pytest

from rentl_agents.tools import (
    AgentTool,
    ContextLookupTool,
    GlossarySearchTool,
    StyleGuideLookupTool,
)
from rentl_schemas.phases import ContextNote, GlossaryTerm, SceneSummary


class TestAgentTool:
    """Test cases for AgentTool base class."""

    def test_create_valid_tool(self) -> None:
        """Test creating a valid agent tool."""

        class MockTool(AgentTool):
            def execute(self, input_data: dict) -> dict:
                return {"result": "success"}

        tool = MockTool(
            name="mock_tool",
            description="Mock tool for testing",
        )

        assert tool.name == "mock_tool"
        assert tool.description == "Mock tool for testing"

    def test_create_tool_with_empty_name(self) -> None:
        """Test creating tool raises error for empty name."""

        class MockTool(AgentTool):
            def execute(self, input_data: dict) -> dict:
                return {"result": "success"}

        with pytest.raises(ValueError, match="Tool name must not be empty"):
            MockTool(
                name="",
                description="Mock tool",
            )

    def test_create_tool_with_empty_description(self) -> None:
        """Test creating tool raises error for empty description."""

        class MockTool(AgentTool):
            def execute(self, input_data: dict) -> dict:
                return {"result": "success"}

        with pytest.raises(ValueError, match="Tool description must not be empty"):
            MockTool(
                name="mock_tool",
                description="",
            )

    def test_tool_schema_property(self) -> None:
        """Test tool schema property."""

        class MockTool(AgentTool):
            def execute(self, input_data: dict) -> dict:
                return {"result": "success"}

        tool = MockTool(
            name="mock_tool",
            description="Mock tool",
        )

        schema = tool.schema

        assert "input" in schema
        assert "output" in schema


class TestContextLookupTool:
    """Test cases for ContextLookupTool class."""

    def test_create_context_lookup_tool(self) -> None:
        """Test creating a context lookup tool."""
        tool = ContextLookupTool()

        assert tool.name == "context_lookup"
        assert "scene" in tool.description.lower()
        assert "note" in tool.description.lower()

    def test_execute_with_scene_id(self) -> None:
        """Test executing context lookup by scene ID."""
        scene_summaries = [
            SceneSummary(
                scene_id="scene_1",
                summary="Scene 1 summary",
                characters=["Alice", "Bob"],
            ),
            SceneSummary(
                scene_id="scene_2",
                summary="Scene 2 summary",
                characters=["Charlie"],
            ),
        ]

        tool = ContextLookupTool(scene_summaries=scene_summaries)

        result = tool.execute({"scene_id": "scene_1"})

        assert isinstance(result, dict)
        assert len(result["scene_summaries"]) == 1
        assert result["scene_summaries"][0]["scene_id"] == "scene_1"

    def test_execute_with_line_id(self) -> None:
        """Test executing context lookup by line ID."""
        context_notes = [
            ContextNote(
                note_id=uuid7(),
                line_id="line_1",
                note="Note for line 1",
            ),
            ContextNote(
                note_id=uuid7(),
                line_id="line_2",
                note="Note for line 2",
            ),
        ]

        tool = ContextLookupTool(context_notes=context_notes)

        result = tool.execute({"line_id": "line_1"})

        assert isinstance(result, dict)
        assert len(result["context_notes"]) == 1
        assert result["context_notes"][0]["line_id"] == "line_1"

    def test_execute_with_invalid_input(self) -> None:
        """Test executing tool with invalid input raises error."""
        tool = ContextLookupTool()

        with pytest.raises(RuntimeError, match="Invalid input"):
            tool.execute({"invalid_field": "value"})

    def test_execute_with_no_results(self) -> None:
        """Test executing tool with no matching results."""
        tool = ContextLookupTool()

        result = tool.execute({"scene_id": "other_1"})

        assert isinstance(result, dict)
        assert len(result["scene_summaries"]) == 0
        assert len(result["context_notes"]) == 0


class TestGlossarySearchTool:
    """Test cases for GlossarySearchTool class."""

    def test_create_glossary_search_tool(self) -> None:
        """Test creating a glossary search tool."""
        tool = GlossarySearchTool()

        assert tool.name == "glossary_search"
        assert "glossary" in tool.description.lower()
        assert "search" in tool.description.lower()

    def test_execute_with_keyword(self) -> None:
        """Test executing glossary search by keyword."""
        glossary_terms = [
            GlossaryTerm(
                term="Hello",
                translation="こんにちは",
                notes="Common greeting",
            ),
            GlossaryTerm(
                term="Goodbye",
                translation="さようなら",
                notes="Common farewell",
            ),
        ]

        tool = GlossarySearchTool(glossary_terms=glossary_terms)

        result = tool.execute({"keyword": "hello"})

        assert isinstance(result, dict)
        assert len(result["terms"]) == 1
        assert result["terms"][0]["term"] == "Hello"

    def test_execute_with_exact_match(self) -> None:
        """Test executing glossary search with exact match."""
        glossary_terms = [
            GlossaryTerm(
                term="Hello",
                translation="こんにちは",
                notes="Common greeting",
            ),
            GlossaryTerm(
                term="Hello World",
                translation="こんにちは世界",
                notes="Phrase",
            ),
        ]

        tool = GlossarySearchTool(glossary_terms=glossary_terms)

        result = tool.execute({"keyword": "hello", "exact_match": True})

        assert isinstance(result, dict)
        assert len(result["terms"]) == 1
        assert result["terms"][0]["term"] == "Hello"

    def test_execute_with_partial_match(self) -> None:
        """Test executing glossary search with partial match."""
        glossary_terms = [
            GlossaryTerm(
                term="Hello World",
                translation="こんにちは世界",
                notes="Phrase",
            ),
        ]

        tool = GlossarySearchTool(glossary_terms=glossary_terms)

        result = tool.execute({"keyword": "hello", "exact_match": False})

        assert isinstance(result, dict)
        assert len(result["terms"]) == 1

    def test_execute_with_invalid_input(self) -> None:
        """Test executing tool with invalid input raises error."""
        tool = GlossarySearchTool()

        with pytest.raises(RuntimeError, match="Invalid input"):
            tool.execute({"missing_keyword": "test"})

    def test_execute_with_no_results(self) -> None:
        """Test executing tool with no matching results."""
        tool = GlossarySearchTool()

        result = tool.execute({"keyword": "nonexistent"})

        assert isinstance(result, dict)
        assert len(result["terms"]) == 0


class TestStyleGuideLookupTool:
    """Test cases for StyleGuideLookupTool class."""

    def test_create_style_guide_lookup_tool(self) -> None:
        """Test creating a style guide lookup tool."""
        content = "# General\nUse formal tone.\n\n# Names\nHonorifics required."
        tool = StyleGuideLookupTool(style_guide_content=content)

        assert tool.name == "style_guide_lookup"
        assert "style guide" in tool.description.lower()
        assert "lookup" in tool.description.lower()

    def test_execute_with_section(self) -> None:
        """Test executing style guide lookup by section."""
        content = (
            "# General\nUse formal tone.\n\n"
            "# Names\nHonorifics required.\n\n"
            "# Dates\nUse YYYY-MM-DD format."
        )
        tool = StyleGuideLookupTool(style_guide_content=content)

        result = tool.execute({"section": "Names"})

        assert isinstance(result, dict)
        assert "Honorifics required" in result["content"]
        assert result["section"] == "Names"

    def test_execute_with_keyword(self) -> None:
        """Test executing style guide lookup by keyword."""
        content = (
            "# General\nUse formal tone and proper honorifics.\n\n"
            "# Names\nHonorifics required."
        )
        tool = StyleGuideLookupTool(style_guide_content=content)

        result = tool.execute({"keyword": "honorifics"})

        assert isinstance(result, dict)
        assert "honorifics" in result["content"].lower()

    def test_execute_without_filters(self) -> None:
        """Test executing style guide lookup without filters."""
        content = "# General\nUse formal tone.\n"
        tool = StyleGuideLookupTool(style_guide_content=content)

        result = tool.execute({})

        assert isinstance(result, dict)
        assert "Use formal tone" in result["content"]

    def test_execute_with_invalid_input(self) -> None:
        """Test executing tool with invalid input raises error."""
        content = "# General\nUse formal tone.\n"
        tool = StyleGuideLookupTool(style_guide_content=content)

        with pytest.raises(RuntimeError, match="Invalid input"):
            tool.execute({"invalid": "test"})
