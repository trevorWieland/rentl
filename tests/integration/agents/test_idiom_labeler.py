"""BDD integration tests for idiom labeler profile loading."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pytest_bdd import given, scenarios, then, when

from rentl_agents import (
    PretranslationIdiomLabelerAgent,
    get_default_agents_dir,
    get_default_prompts_dir,
    load_agent_profile,
)
from rentl_agents.runtime import ProfileAgentConfig
from rentl_agents.wiring import create_pretranslation_agent_from_profile
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.primitives import PhaseName

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/agents/idiom_labeler.feature")


class IdiomLabelerContext:
    """Context object for idiom labeler BDD scenarios."""

    profile: AgentProfileConfig | None = None
    profile_path: Path | None = None
    prompts_dir: Path | None = None
    agent: PretranslationIdiomLabelerAgent | None = None
    error: Exception | None = None


# ============================================================================
# Scenario: Load idiom labeler profile
# ============================================================================


@given(
    "an idiom labeler profile exists at the default location",
    target_fixture="ctx",
)
def given_idiom_labeler_profile_exists() -> IdiomLabelerContext:
    """Verify the idiom labeler profile exists.

    Returns:
        IdiomLabelerContext with paths set.
    """
    ctx = IdiomLabelerContext()
    agents_dir = get_default_agents_dir()
    ctx.profile_path = agents_dir / "pretranslation" / "idiom_labeler.toml"
    ctx.prompts_dir = get_default_prompts_dir()

    # Verify files exist
    assert ctx.profile_path.exists(), f"Profile not found: {ctx.profile_path}"
    assert ctx.prompts_dir.exists(), f"Prompts dir not found: {ctx.prompts_dir}"

    return ctx


@when("I load the agent profile")
def when_load_agent_profile(ctx: IdiomLabelerContext) -> None:
    """Load the agent profile from TOML."""
    assert ctx.profile_path is not None
    ctx.profile = load_agent_profile(ctx.profile_path)


@then("the profile has the correct pretranslation metadata")
def then_profile_has_correct_metadata(ctx: IdiomLabelerContext) -> None:
    """Assert profile metadata is correct."""
    assert ctx.profile is not None
    assert ctx.profile.meta.name == "idiom_labeler"
    assert ctx.profile.meta.phase == PhaseName.PRETRANSLATION
    assert ctx.profile.meta.output_schema == "IdiomAnnotationList"


@then("the profile does not require scene_id")
def then_profile_does_not_require_scene_id(ctx: IdiomLabelerContext) -> None:
    """Assert profile does not require scene_id."""
    assert ctx.profile is not None
    assert ctx.profile.requirements.scene_id_required is False


@then("the profile has valid prompt templates for pretranslation")
def then_profile_has_valid_prompts(ctx: IdiomLabelerContext) -> None:
    """Assert profile has valid prompt templates."""
    assert ctx.profile is not None
    assert ctx.profile.prompts.agent.content
    assert ctx.profile.prompts.user_template.content
    # Check for expected template variables
    assert "{{source_lines}}" in ctx.profile.prompts.user_template.content


# ============================================================================
# Scenario: Create pretranslation agent from profile
# ============================================================================


@given(
    "the idiom labeler profile and prompt layers are loaded",
    target_fixture="ctx",
)
def given_profile_and_layers_loaded() -> IdiomLabelerContext:
    """Load the profile and prompt layers.

    Returns:
        IdiomLabelerContext with profile loaded.
    """
    ctx = IdiomLabelerContext()
    ctx.profile_path = (
        get_default_agents_dir() / "pretranslation" / "idiom_labeler.toml"
    )
    ctx.prompts_dir = get_default_prompts_dir()
    ctx.profile = load_agent_profile(ctx.profile_path)
    return ctx


@when("I create a pretranslation agent from the profile")
def when_create_pretranslation_agent(ctx: IdiomLabelerContext) -> None:
    """Create pretranslation agent from profile."""
    assert ctx.profile_path is not None
    assert ctx.prompts_dir is not None

    config = ProfileAgentConfig(
        api_key="test-key",  # Not used for this test
        model_id="gpt-5-nano",
    )

    ctx.agent = create_pretranslation_agent_from_profile(
        profile_path=ctx.profile_path,
        prompts_dir=ctx.prompts_dir,
        config=config,
    )


@then("the agent can be used with the orchestrator")
def then_agent_can_be_used(ctx: IdiomLabelerContext) -> None:
    """Assert the agent is properly created."""
    assert ctx.agent is not None
    assert isinstance(ctx.agent, PretranslationIdiomLabelerAgent)
    # The agent should have a run method
    assert hasattr(ctx.agent, "run")
    assert callable(ctx.agent.run)


# ============================================================================
# Scenario: Profile validation allows pretranslation variables
# ============================================================================


@given(
    "an idiom labeler profile with pretranslation template variables",
    target_fixture="ctx",
)
def given_profile_with_pretranslation_variables() -> IdiomLabelerContext:
    """Use the default idiom labeler profile which has pretranslation variables.

    Returns:
        IdiomLabelerContext with profile path.
    """
    ctx = IdiomLabelerContext()
    ctx.profile_path = (
        get_default_agents_dir() / "pretranslation" / "idiom_labeler.toml"
    )
    return ctx


@then("the profile loads without validation errors")
def then_profile_loads_without_errors(ctx: IdiomLabelerContext) -> None:
    """Assert profile loaded successfully."""
    assert ctx.profile is not None
    assert ctx.error is None
