"""BDD integration tests for style guide critic profile loading."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pytest_bdd import given, scenarios, then, when

from rentl_agents import (
    QaStyleGuideCriticAgent,
    get_default_agents_dir,
    get_default_prompts_dir,
    load_agent_profile,
)
from rentl_agents.runtime import ProfileAgentConfig
from rentl_agents.wiring import create_qa_agent_from_profile
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.primitives import PhaseName

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/agents/style_guide_critic.feature")


class StyleGuideCriticContext:
    """Context object for style guide critic BDD scenarios."""

    profile: AgentProfileConfig | None = None
    profile_path: Path | None = None
    prompts_dir: Path | None = None
    agent: QaStyleGuideCriticAgent | None = None
    error: Exception | None = None


# ============================================================================
# Scenario: Load style guide critic profile
# ============================================================================


@given(
    "a style guide critic profile exists at the default location",
    target_fixture="ctx",
)
def given_style_guide_critic_profile_exists() -> StyleGuideCriticContext:
    """Verify the style guide critic profile exists.

    Returns:
        StyleGuideCriticContext with paths set.
    """
    ctx = StyleGuideCriticContext()
    agents_dir = get_default_agents_dir()
    ctx.profile_path = agents_dir / "qa" / "style_guide_critic.toml"
    ctx.prompts_dir = get_default_prompts_dir()

    # Verify files exist
    assert ctx.profile_path.exists(), f"Profile not found: {ctx.profile_path}"
    assert ctx.prompts_dir.exists(), f"Prompts dir not found: {ctx.prompts_dir}"

    return ctx


@when("I load the agent profile")
def when_load_agent_profile(ctx: StyleGuideCriticContext) -> None:
    """Load the agent profile from TOML."""
    assert ctx.profile_path is not None
    ctx.profile = load_agent_profile(ctx.profile_path)


@then("the profile has the correct QA metadata")
def then_profile_has_correct_qa_metadata(ctx: StyleGuideCriticContext) -> None:
    """Assert profile metadata is correct."""
    assert ctx.profile is not None
    assert ctx.profile.meta.name == "style_guide_critic"
    assert ctx.profile.meta.phase == PhaseName.QA
    assert ctx.profile.meta.output_schema == "StyleGuideViolationList"


@then("the profile does not require scene_id")
def then_profile_does_not_require_scene_id(ctx: StyleGuideCriticContext) -> None:
    """Assert profile does not require scene_id."""
    assert ctx.profile is not None
    assert ctx.profile.requirements.scene_id_required is False


@then("the profile has valid prompt templates for QA")
def then_profile_has_valid_qa_prompts(ctx: StyleGuideCriticContext) -> None:
    """Assert profile has valid prompt templates."""
    assert ctx.profile is not None
    assert ctx.profile.prompts.agent.content
    assert ctx.profile.prompts.user_template.content
    # Check for expected template variables
    assert "{{style_guide}}" in ctx.profile.prompts.user_template.content
    assert "{{lines_to_review}}" in ctx.profile.prompts.user_template.content


# ============================================================================
# Scenario: Create QA agent from profile
# ============================================================================


@given(
    "the style guide critic profile and prompt layers are loaded",
    target_fixture="ctx",
)
def given_profile_and_layers_loaded() -> StyleGuideCriticContext:
    """Load the profile and prompt layers.

    Returns:
        StyleGuideCriticContext with profile loaded.
    """
    ctx = StyleGuideCriticContext()
    ctx.profile_path = get_default_agents_dir() / "qa" / "style_guide_critic.toml"
    ctx.prompts_dir = get_default_prompts_dir()
    ctx.profile = load_agent_profile(ctx.profile_path)
    return ctx


@when("I create a QA agent from the profile")
def when_create_qa_agent(ctx: StyleGuideCriticContext) -> None:
    """Create QA agent from profile."""
    assert ctx.profile_path is not None
    assert ctx.prompts_dir is not None

    config = ProfileAgentConfig(
        api_key="test-key",  # Not used for this test
        model_id="gpt-4o-mini",
    )

    ctx.agent = create_qa_agent_from_profile(
        profile_path=ctx.profile_path,
        prompts_dir=ctx.prompts_dir,
        config=config,
    )


@then("the agent can be used with the orchestrator")
def then_agent_can_be_used(ctx: StyleGuideCriticContext) -> None:
    """Assert the agent is properly created."""
    assert ctx.agent is not None
    assert isinstance(ctx.agent, QaStyleGuideCriticAgent)
    # The agent should have a run method
    assert hasattr(ctx.agent, "run")
    assert callable(ctx.agent.run)


# ============================================================================
# Scenario: Profile validation allows QA variables
# ============================================================================


@given(
    "a style guide critic profile with QA template variables",
    target_fixture="ctx",
)
def given_profile_with_qa_variables() -> StyleGuideCriticContext:
    """Use the default style guide critic profile which has QA variables.

    Returns:
        StyleGuideCriticContext with profile path.
    """
    ctx = StyleGuideCriticContext()
    ctx.profile_path = get_default_agents_dir() / "qa" / "style_guide_critic.toml"
    return ctx


@then("the profile loads without validation errors")
def then_profile_loads_without_errors(ctx: StyleGuideCriticContext) -> None:
    """Assert profile loaded successfully."""
    assert ctx.profile is not None
    assert ctx.error is None
