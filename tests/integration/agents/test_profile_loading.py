"""BDD integration tests for profile agent loading."""

from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from uuid import uuid7

from pytest_bdd import given, scenarios, then, when

from rentl_agents import (
    ContextSceneSummarizerAgent,
    SceneValidationError,
    TemplateValidationError,
    get_default_agents_dir,
    get_default_prompts_dir,
    load_agent_profile,
)
from rentl_agents.profiles.loader import AgentProfileLoadError
from rentl_agents.runtime import ProfileAgentConfig
from rentl_agents.wiring import create_context_agent_from_profile
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.io import SourceLine
from rentl_schemas.phases import ContextPhaseInput
from rentl_schemas.primitives import PhaseName

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/agents/profile_loading.feature")


class ProfileLoadingContext:
    """Context object for profile loading BDD scenarios."""

    profile: AgentProfileConfig | None = None
    profile_path: Path | None = None
    prompts_dir: Path | None = None
    agent: ContextSceneSummarizerAgent | None = None
    error: Exception | None = None
    source_lines: list[SourceLine] | None = None
    temp_dir: TemporaryDirectory[str] | None = None


# ============================================================================
# Scenario: Load scene summarizer profile
# ============================================================================


@given(
    "a scene summarizer profile exists at the default location",
    target_fixture="ctx",
)
def given_scene_summarizer_profile_exists() -> ProfileLoadingContext:
    """Verify the scene summarizer profile exists.

    Returns:
        ProfileLoadingContext with paths set.
    """
    ctx = ProfileLoadingContext()
    agents_dir = get_default_agents_dir()
    ctx.profile_path = agents_dir / "context" / "scene_summarizer.toml"
    ctx.prompts_dir = get_default_prompts_dir()

    # Verify files exist
    assert ctx.profile_path.exists(), f"Profile not found: {ctx.profile_path}"
    assert ctx.prompts_dir.exists(), f"Prompts dir not found: {ctx.prompts_dir}"

    return ctx


@when("I load the agent profile")
def when_load_agent_profile(ctx: ProfileLoadingContext) -> None:
    """Load the agent profile from TOML."""
    assert ctx.profile_path is not None
    ctx.profile = load_agent_profile(ctx.profile_path)


@then("the profile has the correct metadata")
def then_profile_has_correct_metadata(ctx: ProfileLoadingContext) -> None:
    """Assert profile metadata is correct."""
    assert ctx.profile is not None
    assert ctx.profile.meta.name == "scene_summarizer"
    assert ctx.profile.meta.phase == PhaseName.CONTEXT
    assert ctx.profile.meta.output_schema == "SceneSummary"


@then("the profile requires scene_id")
def then_profile_requires_scene_id(ctx: ProfileLoadingContext) -> None:
    """Assert profile requires scene_id."""
    assert ctx.profile is not None
    assert ctx.profile.requirements.scene_id_required is True


@then("the profile has valid prompt templates")
def then_profile_has_valid_prompts(ctx: ProfileLoadingContext) -> None:
    """Assert profile has valid prompt templates."""
    assert ctx.profile is not None
    assert ctx.profile.prompts.agent.content
    assert ctx.profile.prompts.user_template.content
    # Check for expected template variables
    assert "{{scene_id}}" in ctx.profile.prompts.user_template.content


# ============================================================================
# Scenario: Profile validation catches unknown variables
# ============================================================================


@given(
    "an agent profile with unknown template variables",
    target_fixture="ctx",
)
def given_profile_with_unknown_variables() -> ProfileLoadingContext:
    """Create a profile with unknown template variables.

    Returns:
        ProfileLoadingContext with invalid profile path.
    """
    ctx = ProfileLoadingContext()
    ctx.temp_dir = TemporaryDirectory()
    temp_path = Path(ctx.temp_dir.name)

    # Create invalid profile with unknown variable
    profile_content = """
[meta]
name = "invalid_agent"
version = "1.0.0"
phase = "context"
description = "Invalid agent for testing"
output_schema = "SceneSummary"

[requirements]
scene_id_required = true

[orchestration]
priority = 10

[prompts]
agent = "This is a prompt"
user_template = "{{unknown_variable_xyz}}"

[tools]
allowed = []

[model_hints]
recommended = ["gpt-4o"]
"""
    profile_path = temp_path / "invalid.toml"
    profile_path.write_text(profile_content)
    ctx.profile_path = profile_path

    return ctx


@when("I attempt to load the agent profile")
def when_attempt_load_profile(ctx: ProfileLoadingContext) -> None:
    """Attempt to load the profile (may fail)."""
    assert ctx.profile_path is not None
    try:
        ctx.profile = load_agent_profile(ctx.profile_path)
    except (TemplateValidationError, AgentProfileLoadError) as e:
        ctx.error = e


@then("an error is raised mentioning the unknown variables")
def then_error_mentions_unknown_variables(ctx: ProfileLoadingContext) -> None:
    """Assert error is raised for unknown variables."""
    assert ctx.error is not None
    # The error message should mention the unknown variable
    error_str = str(ctx.error)
    assert "unknown" in error_str.lower() or "variable" in error_str.lower()

    # Cleanup
    if ctx.temp_dir:
        ctx.temp_dir.cleanup()


# ============================================================================
# Scenario: Create context agent from profile
# ============================================================================


@given(
    "the scene summarizer profile and prompt layers are loaded",
    target_fixture="ctx",
)
def given_profile_and_layers_loaded() -> ProfileLoadingContext:
    """Load the profile and prompt layers.

    Returns:
        ProfileLoadingContext with profile loaded.
    """
    ctx = ProfileLoadingContext()
    ctx.profile_path = get_default_agents_dir() / "context" / "scene_summarizer.toml"
    ctx.prompts_dir = get_default_prompts_dir()
    ctx.profile = load_agent_profile(ctx.profile_path)
    return ctx


@when("I create a context agent from the profile")
def when_create_context_agent(ctx: ProfileLoadingContext) -> None:
    """Create context agent from profile."""
    assert ctx.profile_path is not None
    assert ctx.prompts_dir is not None

    config = ProfileAgentConfig(
        api_key="test-key",  # Not used for this test
        model_id="gpt-4o-mini",
    )

    ctx.agent = create_context_agent_from_profile(
        profile_path=ctx.profile_path,
        prompts_dir=ctx.prompts_dir,
        config=config,
    )


@then("the agent can be used with the orchestrator")
def then_agent_can_be_used(ctx: ProfileLoadingContext) -> None:
    """Assert the agent is properly created."""
    assert ctx.agent is not None
    assert isinstance(ctx.agent, ContextSceneSummarizerAgent)
    # The agent should have a run method
    assert hasattr(ctx.agent, "run")
    assert callable(ctx.agent.run)


# ============================================================================
# Scenario: Scene validation rejects lines without scene_id
# ============================================================================


@given("a context agent created from profile", target_fixture="ctx")
def given_context_agent_created() -> ProfileLoadingContext:
    """Create a context agent from profile.

    Returns:
        ProfileLoadingContext with agent created.
    """
    ctx = ProfileLoadingContext()
    ctx.profile_path = get_default_agents_dir() / "context" / "scene_summarizer.toml"
    ctx.prompts_dir = get_default_prompts_dir()

    config = ProfileAgentConfig(
        api_key="test-key",
        model_id="gpt-4o-mini",
    )

    ctx.agent = create_context_agent_from_profile(
        profile_path=ctx.profile_path,
        prompts_dir=ctx.prompts_dir,
        config=config,
    )
    return ctx


@given("source lines without scene_id")
def given_lines_without_scene_id(ctx: ProfileLoadingContext) -> None:
    """Create source lines without scene_id."""
    ctx.source_lines = [
        SourceLine(
            line_id="line_001",
            text="Hello world",
            route_id="main_001",  # Valid route_id format
            scene_id=None,  # Missing scene_id
        ),
    ]


@when("I run the agent")
def when_run_agent(ctx: ProfileLoadingContext) -> None:
    """Run the agent (should fail)."""
    assert ctx.agent is not None
    assert ctx.source_lines is not None

    payload = ContextPhaseInput(
        run_id=uuid7(),
        source_lines=ctx.source_lines,
    )

    try:
        # Use asyncio.run for Python 3.7+ compatible async execution
        asyncio.run(ctx.agent.run(payload))
    except SceneValidationError as e:
        ctx.error = e


@then("a SceneValidationError is raised")
def then_scene_validation_error_raised(ctx: ProfileLoadingContext) -> None:
    """Assert SceneValidationError is raised."""
    assert ctx.error is not None
    assert isinstance(ctx.error, SceneValidationError)


@then("the error suggests using BatchSummarizer")
def then_error_suggests_batch_summarizer(ctx: ProfileLoadingContext) -> None:
    """Assert error message suggests BatchSummarizer."""
    assert ctx.error is not None
    assert "BatchSummarizer" in str(ctx.error)
