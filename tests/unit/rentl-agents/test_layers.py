"""Unit tests for prompt layer system."""

from __future__ import annotations

from pathlib import Path

import pytest

from rentl_agents.layers import (
    LayerLoadError,
    PromptComposer,
    PromptLayerRegistry,
    _load_phase_prompt_sync,
    _load_root_prompt_sync,
    load_layer_registry,
    load_phase_prompt,
    load_phase_prompt_async,
    load_root_prompt,
    load_root_prompt_async,
)
from rentl_agents.templates import TemplateContext
from rentl_schemas.agents import (
    AgentProfileConfig,
    AgentProfileMeta,
    AgentPromptConfig,
    AgentPromptContent,
    PhasePromptConfig,
    PromptLayerContent,
    RootPromptConfig,
)
from rentl_schemas.primitives import PhaseName


class TestPromptLayerRegistry:
    """Test cases for PromptLayerRegistry."""

    def test_empty_registry(self) -> None:
        """Test empty registry state."""
        registry = PromptLayerRegistry()

        assert registry.root is None
        assert not registry.has_root()
        assert not registry.has_phase(PhaseName.CONTEXT)
        assert registry.get_phase(PhaseName.CONTEXT) is None

    def test_set_and_get_root(self) -> None:
        """Test setting and getting root layer."""
        registry = PromptLayerRegistry()
        root_config = RootPromptConfig(
            system=PromptLayerContent(content="Root prompt content")
        )

        registry.set_root(root_config)

        assert registry.has_root()
        assert registry.root == root_config

    def test_set_and_get_phase(self) -> None:
        """Test setting and getting phase layers."""
        registry = PromptLayerRegistry()
        phase_config = PhasePromptConfig(
            phase=PhaseName.CONTEXT,
            output_language="source",
            system=PromptLayerContent(content="Context phase prompt"),
        )

        registry.set_phase(phase_config)

        assert registry.has_phase(PhaseName.CONTEXT)
        assert registry.get_phase(PhaseName.CONTEXT) == phase_config
        assert not registry.has_phase(PhaseName.TRANSLATE)


class TestLoadRootPrompt:
    """Test cases for load_root_prompt functions."""

    def test_load_valid_root_prompt(self, tmp_path: Path) -> None:
        """Test loading a valid root prompt."""
        root_content = """
[system]
content = \"\"\"
You are part of a localization team working on {{game_name}}.
{{game_synopsis}}
\"\"\"
"""
        root_path = tmp_path / "root.toml"
        root_path.write_text(root_content)

        config = load_root_prompt(root_path)

        assert isinstance(config, RootPromptConfig)
        assert "{{game_name}}" in config.system.content

    def test_load_missing_root_file(self, tmp_path: Path) -> None:
        """Test loading non-existent root file raises error."""
        missing_path = tmp_path / "nonexistent.toml"

        with pytest.raises(LayerLoadError) as exc_info:
            load_root_prompt(missing_path)

        assert exc_info.value.layer_name == "root"

    def test_load_invalid_root_toml(self, tmp_path: Path) -> None:
        """Test loading invalid TOML raises error."""
        root_path = tmp_path / "root.toml"
        root_path.write_text("invalid toml [[[")

        with pytest.raises(LayerLoadError):
            load_root_prompt(root_path)

    def test_load_root_unknown_variable(self, tmp_path: Path) -> None:
        """Test loading root with unknown variable raises error."""
        root_content = """
[system]
content = "Using {{unknown_variable}}"
"""
        root_path = tmp_path / "root.toml"
        root_path.write_text(root_content)

        with pytest.raises(LayerLoadError):
            load_root_prompt(root_path)


class TestLoadRootPromptAsync:
    """Test cases for async root prompt loading."""

    @pytest.mark.asyncio
    async def test_load_valid_root_async(self, tmp_path: Path) -> None:
        """Test loading root prompt asynchronously."""
        root_content = """
[system]
content = "Async root prompt for {{game_name}}"
"""
        root_path = tmp_path / "root.toml"
        root_path.write_text(root_content)

        config = await load_root_prompt_async(root_path)

        assert isinstance(config, RootPromptConfig)

    @pytest.mark.asyncio
    async def test_load_missing_root_async(self, tmp_path: Path) -> None:
        """Test async loading of non-existent root raises error."""
        missing_path = tmp_path / "nonexistent.toml"

        with pytest.raises(LayerLoadError):
            await load_root_prompt_async(missing_path)


class TestLoadRootPromptSync:
    """Test cases for sync root prompt helper."""

    def test_load_root_sync_helper(self, tmp_path: Path) -> None:
        """Test the internal sync helper function."""
        root_content = """
[system]
content = "Sync root prompt"
"""
        root_path = tmp_path / "root.toml"
        root_path.write_text(root_content)

        config = _load_root_prompt_sync(root_path)

        assert isinstance(config, RootPromptConfig)


class TestLoadPhasePrompt:
    """Test cases for load_phase_prompt functions."""

    def test_load_valid_phase_prompt(self, tmp_path: Path) -> None:
        """Test loading a valid phase prompt."""
        phase_content = """
phase = "context"
output_language = "source"

[system]
content = "You are on the Context team. Output in {{source_lang}}."
"""
        phase_path = tmp_path / "context.toml"
        phase_path.write_text(phase_content)

        config = load_phase_prompt(phase_path)

        assert isinstance(config, PhasePromptConfig)
        assert config.phase == PhaseName.CONTEXT
        assert config.output_language == "source"

    def test_load_phase_with_meta_format(self, tmp_path: Path) -> None:
        """Test loading phase prompt with nested meta.phase format."""
        phase_content = """
[meta]
phase = "translate"

output_language = "target"

[system]
content = "You are on the Translation team."
"""
        phase_path = tmp_path / "translate.toml"
        phase_path.write_text(phase_content)

        config = load_phase_prompt(phase_path)

        assert config.phase == PhaseName.TRANSLATE

    def test_load_missing_phase_file(self, tmp_path: Path) -> None:
        """Test loading non-existent phase file raises error."""
        missing_path = tmp_path / "nonexistent.toml"

        with pytest.raises(LayerLoadError) as exc_info:
            load_phase_prompt(missing_path)

        assert exc_info.value.layer_name == "phase"


class TestLoadPhasePromptAsync:
    """Test cases for async phase prompt loading."""

    @pytest.mark.asyncio
    async def test_load_valid_phase_async(self, tmp_path: Path) -> None:
        """Test loading phase prompt asynchronously."""
        phase_content = """
phase = "context"

[system]
content = "Async phase prompt"
"""
        phase_path = tmp_path / "context.toml"
        phase_path.write_text(phase_content)

        config = await load_phase_prompt_async(phase_path)

        assert isinstance(config, PhasePromptConfig)

    @pytest.mark.asyncio
    async def test_load_missing_phase_async(self, tmp_path: Path) -> None:
        """Test async loading of non-existent phase raises error."""
        missing_path = tmp_path / "nonexistent.toml"

        with pytest.raises(LayerLoadError):
            await load_phase_prompt_async(missing_path)


class TestLoadPhasePromptSync:
    """Test cases for sync phase prompt helper."""

    def test_load_phase_sync_helper(self, tmp_path: Path) -> None:
        """Test the internal sync helper function."""
        phase_content = """
phase = "context"

[system]
content = "Sync phase prompt"
"""
        phase_path = tmp_path / "context.toml"
        phase_path.write_text(phase_content)

        config = _load_phase_prompt_sync(phase_path)

        assert isinstance(config, PhasePromptConfig)


class TestLoadLayerRegistry:
    """Test cases for load_layer_registry function."""

    def test_load_empty_directory(self, tmp_path: Path) -> None:
        """Test loading from empty directory returns empty registry."""
        registry = load_layer_registry(tmp_path)

        assert not registry.has_root()
        assert not registry.has_phase(PhaseName.CONTEXT)

    def test_load_full_registry(self, tmp_path: Path) -> None:
        """Test loading complete prompt layer registry."""
        # Create root.toml
        root_content = """
[system]
content = "Root prompt for {{game_name}}"
"""
        (tmp_path / "root.toml").write_text(root_content)

        # Create phases directory
        phases_dir = tmp_path / "phases"
        phases_dir.mkdir()

        # Create context.toml
        context_content = """
phase = "context"

[system]
content = "Context team prompt"
"""
        (phases_dir / "context.toml").write_text(context_content)

        registry = load_layer_registry(tmp_path)

        assert registry.has_root()
        assert registry.has_phase(PhaseName.CONTEXT)
        assert not registry.has_phase(PhaseName.TRANSLATE)


class TestPromptComposer:
    """Test cases for PromptComposer."""

    def test_compose_with_all_layers(self) -> None:
        """Test composing system prompt with all layers."""
        registry = PromptLayerRegistry()
        registry.set_root(
            RootPromptConfig(system=PromptLayerContent(content="Root: {{game_name}}"))
        )
        registry.set_phase(
            PhasePromptConfig(
                phase=PhaseName.CONTEXT,
                output_language="source",
                system=PromptLayerContent(content="Phase: Context team"),
            )
        )

        composer = PromptComposer(registry=registry)

        agent_profile = AgentProfileConfig(
            meta=AgentProfileMeta(
                name="test_agent",
                version="1.0.0",
                phase=PhaseName.CONTEXT,
                description="Test agent",
                output_schema="SceneSummary",
            ),
            prompts=AgentPromptConfig(
                agent=AgentPromptContent(content="Agent: Scene summarizer"),
                user_template=AgentPromptContent(content="{{scene_id}}"),
            ),
        )

        context = TemplateContext(
            root_variables={"game_name": "Test Game"},
        )

        result = composer.compose_system_prompt(agent_profile, context)

        assert "Root: Test Game" in result
        assert "Phase: Context team" in result
        assert "Agent: Scene summarizer" in result

    def test_compose_without_root(self) -> None:
        """Test composing without root layer."""
        registry = PromptLayerRegistry()
        registry.set_phase(
            PhasePromptConfig(
                phase=PhaseName.CONTEXT,
                output_language="source",
                system=PromptLayerContent(content="Phase only"),
            )
        )

        composer = PromptComposer(registry=registry)

        agent_profile = AgentProfileConfig(
            meta=AgentProfileMeta(
                name="test_agent",
                version="1.0.0",
                phase=PhaseName.CONTEXT,
                description="Test agent",
                output_schema="SceneSummary",
            ),
            prompts=AgentPromptConfig(
                agent=AgentPromptContent(content="Agent prompt"),
                user_template=AgentPromptContent(content="{{scene_id}}"),
            ),
        )

        context = TemplateContext()

        result = composer.compose_system_prompt(agent_profile, context)

        assert "Phase only" in result
        assert "Agent prompt" in result

    def test_render_user_prompt(self) -> None:
        """Test rendering user prompt template."""
        registry = PromptLayerRegistry()
        composer = PromptComposer(registry=registry)

        agent_profile = AgentProfileConfig(
            meta=AgentProfileMeta(
                name="test_agent",
                version="1.0.0",
                phase=PhaseName.CONTEXT,
                description="Test agent",
                output_schema="SceneSummary",
            ),
            prompts=AgentPromptConfig(
                agent=AgentPromptContent(content="Agent"),
                user_template=AgentPromptContent(
                    content="Scene: {{scene_id}}\nLines: {{scene_lines}}"
                ),
            ),
        )

        context = TemplateContext(
            agent_variables={
                "scene_id": "scene_001",
                "scene_lines": "Line 1\nLine 2",
            }
        )

        result = composer.render_user_prompt(agent_profile, context)

        assert "Scene: scene_001" in result
        assert "Lines: Line 1\nLine 2" in result


class TestLayerLoadError:
    """Test cases for LayerLoadError."""

    def test_error_attributes(self) -> None:
        """Test LayerLoadError has correct attributes."""
        error = LayerLoadError(
            "Failed to load",
            layer_name="root",
            source_path=Path("/path/to/root.toml"),
        )

        assert error.layer_name == "root"
        assert error.source_path == Path("/path/to/root.toml")
        assert "Failed to load" in str(error)
