"""Unit tests for agent profile loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from rentl_agents.profiles.loader import (
    AgentProfileLoadError,
    SchemaResolutionError,
    ToolResolutionError,
    _load_agent_profile_sync,
    load_agent_profile,
    load_agent_profile_async,
    resolve_output_schema,
)
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.primitives import PhaseName


class TestLoadAgentProfile:
    """Test cases for load_agent_profile functions."""

    def test_load_valid_profile(self, tmp_path: Path) -> None:
        """Test loading a valid agent profile."""
        profile_content = """
[meta]
name = "test_agent"
version = "1.0.0"
phase = "context"
description = "Test agent for unit testing"
output_schema = "SceneSummary"

[requirements]
scene_id_required = true

[orchestration]
priority = 10
depends_on = []

[prompts.agent]
content = "You are a test agent."

[prompts.user_template]
content = "Scene: {{scene_id}}\\n{{scene_lines}}"

[tools]
allowed = []

[model_hints]
recommended = ["gpt-4o"]
"""
        profile_path = tmp_path / "test_agent.toml"
        profile_path.write_text(profile_content)

        profile = load_agent_profile(profile_path)

        assert isinstance(profile, AgentProfileConfig)
        assert profile.meta.name == "test_agent"
        assert profile.meta.phase == PhaseName.CONTEXT
        assert profile.meta.output_schema == "SceneSummary"
        assert profile.requirements.scene_id_required is True

    def test_load_missing_file(self, tmp_path: Path) -> None:
        """Test loading a non-existent profile raises error."""
        missing_path = tmp_path / "nonexistent.toml"

        with pytest.raises(AgentProfileLoadError) as exc_info:
            load_agent_profile(missing_path)

        assert "not found" in str(exc_info.value).lower()

    def test_load_invalid_toml(self, tmp_path: Path) -> None:
        """Test loading invalid TOML raises error."""
        profile_path = tmp_path / "invalid.toml"
        profile_path.write_text("this is not valid toml [[[")

        with pytest.raises(AgentProfileLoadError) as exc_info:
            load_agent_profile(profile_path)

        assert "Invalid TOML" in str(exc_info.value)

    def test_load_invalid_phase(self, tmp_path: Path) -> None:
        """Test loading profile with invalid phase raises error."""
        profile_content = """
[meta]
name = "test_agent"
version = "1.0.0"
phase = "invalid_phase"
description = "Test agent"
output_schema = "SceneSummary"

[prompts.agent]
content = "You are a test agent."

[prompts.user_template]
content = "Test"
"""
        profile_path = tmp_path / "test_agent.toml"
        profile_path.write_text(profile_content)

        with pytest.raises(AgentProfileLoadError) as exc_info:
            load_agent_profile(profile_path)

        assert "Invalid phase name" in str(exc_info.value)

    def test_load_unknown_template_variable(self, tmp_path: Path) -> None:
        """Test loading profile with unknown template variable raises error."""
        profile_content = """
[meta]
name = "test_agent"
version = "1.0.0"
phase = "context"
description = "Test agent"
output_schema = "SceneSummary"

[prompts.agent]
content = "You are a test agent."

[prompts.user_template]
content = "{{unknown_variable_xyz}}"
"""
        profile_path = tmp_path / "test_agent.toml"
        profile_path.write_text(profile_content)

        with pytest.raises(AgentProfileLoadError) as exc_info:
            load_agent_profile(profile_path)

        assert "unknown" in str(exc_info.value).lower()

    def test_load_unknown_output_schema(self, tmp_path: Path) -> None:
        """Test loading profile with unknown output schema raises error."""
        profile_content = """
[meta]
name = "test_agent"
version = "1.0.0"
phase = "context"
description = "Test agent"
output_schema = "NonExistentSchema"

[prompts.agent]
content = "You are a test agent."

[prompts.user_template]
content = "Scene: {{scene_id}}"
"""
        profile_path = tmp_path / "test_agent.toml"
        profile_path.write_text(profile_content)

        with pytest.raises(AgentProfileLoadError) as exc_info:
            load_agent_profile(profile_path)

        assert "schema" in str(exc_info.value).lower()


class TestLoadAgentProfileAsync:
    """Test cases for async agent profile loading."""

    @pytest.mark.asyncio
    async def test_load_valid_profile_async(self, tmp_path: Path) -> None:
        """Test loading a valid agent profile asynchronously."""
        profile_content = """
[meta]
name = "async_test_agent"
version = "1.0.0"
phase = "context"
description = "Async test agent"
output_schema = "SceneSummary"

[requirements]
scene_id_required = false

[orchestration]
priority = 20

[prompts.agent]
content = "You are an async test agent."

[prompts.user_template]
content = "Scene: {{scene_id}}\\nLines: {{scene_lines}}"

[tools]
allowed = []
"""
        profile_path = tmp_path / "async_agent.toml"
        profile_path.write_text(profile_content)

        profile = await load_agent_profile_async(profile_path)

        assert isinstance(profile, AgentProfileConfig)
        assert profile.meta.name == "async_test_agent"
        assert profile.orchestration.priority == 20

    @pytest.mark.asyncio
    async def test_load_missing_file_async(self, tmp_path: Path) -> None:
        """Test async loading of non-existent profile raises error."""
        missing_path = tmp_path / "nonexistent.toml"

        with pytest.raises(AgentProfileLoadError):
            await load_agent_profile_async(missing_path)


class TestLoadAgentProfileSync:
    """Test cases for sync helper function."""

    def test_load_valid_profile_sync_helper(self, tmp_path: Path) -> None:
        """Test the internal sync helper function."""
        profile_content = """
[meta]
name = "sync_test_agent"
version = "1.0.0"
phase = "context"
description = "Sync test agent"
output_schema = "SceneSummary"

[prompts.agent]
content = "You are a sync test agent."

[prompts.user_template]
content = "Scene: {{scene_id}}"
"""
        profile_path = tmp_path / "sync_agent.toml"
        profile_path.write_text(profile_content)

        profile = _load_agent_profile_sync(profile_path)

        assert isinstance(profile, AgentProfileConfig)
        assert profile.meta.name == "sync_test_agent"


class TestResolveOutputSchema:
    """Test cases for output schema resolution."""

    def test_resolve_known_schema(self) -> None:
        """Test resolving a known output schema."""
        schema_class = resolve_output_schema("SceneSummary")
        assert schema_class is not None

    def test_resolve_unknown_schema(self) -> None:
        """Test resolving an unknown schema raises error."""
        with pytest.raises(SchemaResolutionError) as exc_info:
            resolve_output_schema("UnknownSchemaName")

        assert "UnknownSchemaName" in str(exc_info.value)


class TestToolResolutionError:
    """Test cases for tool resolution error."""

    def test_tool_resolution_error_attributes(self) -> None:
        """Test ToolResolutionError has correct attributes."""
        error = ToolResolutionError("Tool not found", tool_name="unknown_tool")

        assert error.tool_name == "unknown_tool"
        assert "Tool not found" in str(error)


class TestAgentProfileLoadError:
    """Test cases for agent profile load error."""

    def test_error_with_agent_name(self) -> None:
        """Test AgentProfileLoadError with agent name."""
        error = AgentProfileLoadError(
            "Failed to load",
            agent_name="test_agent",
            source_path=Path("/path/to/agent.toml"),
        )

        assert error.agent_name == "test_agent"
        assert error.source_path == Path("/path/to/agent.toml")
