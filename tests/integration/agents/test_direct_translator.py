"""BDD integration tests for direct translator profile loading."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pytest_bdd import given, scenarios, then, when

from rentl_agents import (
    TranslateDirectTranslatorAgent,
    get_default_agents_dir,
    get_default_prompts_dir,
    load_agent_profile,
)
from rentl_agents.runtime import ProfileAgentConfig
from rentl_agents.wiring import create_translate_agent_from_profile
from rentl_schemas.agents import AgentProfileConfig
from rentl_schemas.primitives import PhaseName

if TYPE_CHECKING:
    pass

# Link feature file
scenarios("../features/agents/direct_translator.feature")


class DirectTranslatorContext:
    """Context object for direct translator BDD scenarios."""

    profile: AgentProfileConfig | None = None
    profile_path: Path | None = None
    prompts_dir: Path | None = None
    agent: TranslateDirectTranslatorAgent | None = None
    error: Exception | None = None


# ============================================================================
# Scenario: Load direct translator profile
# ============================================================================


@given(
    "a direct translator profile exists at the default location",
    target_fixture="ctx",
)
def given_direct_translator_profile_exists() -> DirectTranslatorContext:
    """Verify the direct translator profile exists.

    Returns:
        DirectTranslatorContext with paths set.
    """
    ctx = DirectTranslatorContext()
    agents_dir = get_default_agents_dir()
    ctx.profile_path = agents_dir / "translate" / "direct_translator.toml"
    ctx.prompts_dir = get_default_prompts_dir()

    # Verify files exist
    assert ctx.profile_path.exists(), f"Profile not found: {ctx.profile_path}"
    assert ctx.prompts_dir.exists(), f"Prompts dir not found: {ctx.prompts_dir}"

    return ctx


@when("I load the agent profile")
def when_load_agent_profile(ctx: DirectTranslatorContext) -> None:
    """Load the agent profile from TOML."""
    assert ctx.profile_path is not None
    ctx.profile = load_agent_profile(ctx.profile_path)


@then("the profile has the correct translate metadata")
def then_profile_has_correct_metadata(ctx: DirectTranslatorContext) -> None:
    """Assert profile metadata is correct."""
    assert ctx.profile is not None
    assert ctx.profile.meta.name == "direct_translator"
    assert ctx.profile.meta.phase == PhaseName.TRANSLATE
    assert ctx.profile.meta.output_schema == "TranslationResultList"


@then("the profile does not require scene_id")
def then_profile_does_not_require_scene_id(ctx: DirectTranslatorContext) -> None:
    """Assert profile does not require scene_id."""
    assert ctx.profile is not None
    assert ctx.profile.requirements.scene_id_required is False


@then("the profile has valid prompt templates for translate")
def then_profile_has_valid_prompts(ctx: DirectTranslatorContext) -> None:
    """Assert profile has valid prompt templates."""
    assert ctx.profile is not None
    assert ctx.profile.prompts.agent.content
    assert ctx.profile.prompts.user_template.content
    # Check for expected template variables
    assert "{{annotated_source_lines}}" in ctx.profile.prompts.user_template.content
    assert "{{source_lang}}" in ctx.profile.prompts.user_template.content
    assert "{{target_lang}}" in ctx.profile.prompts.user_template.content


# ============================================================================
# Scenario: Create translate agent from profile
# ============================================================================


@given(
    "the direct translator profile and prompt layers are loaded",
    target_fixture="ctx",
)
def given_profile_and_layers_loaded() -> DirectTranslatorContext:
    """Load the profile and prompt layers.

    Returns:
        DirectTranslatorContext with profile loaded.
    """
    ctx = DirectTranslatorContext()
    ctx.profile_path = get_default_agents_dir() / "translate" / "direct_translator.toml"
    ctx.prompts_dir = get_default_prompts_dir()
    ctx.profile = load_agent_profile(ctx.profile_path)
    return ctx


@when("I create a translate agent from the profile")
def when_create_translate_agent(ctx: DirectTranslatorContext) -> None:
    """Create translate agent from profile."""
    assert ctx.profile_path is not None
    assert ctx.prompts_dir is not None

    config = ProfileAgentConfig(
        api_key="test-key",  # Not used for this test
        model_id="gpt-5-nano",
    )

    ctx.agent = create_translate_agent_from_profile(
        profile_path=ctx.profile_path,
        prompts_dir=ctx.prompts_dir,
        config=config,
    )


@then("the agent can be used with the orchestrator")
def then_agent_can_be_used(ctx: DirectTranslatorContext) -> None:
    """Assert the agent is properly created."""
    assert ctx.agent is not None
    assert isinstance(ctx.agent, TranslateDirectTranslatorAgent)
    # The agent should have a run method
    assert hasattr(ctx.agent, "run")
    assert callable(ctx.agent.run)


# ============================================================================
# Scenario: Profile validation allows translate variables
# ============================================================================


@given(
    "a direct translator profile with translate template variables",
    target_fixture="ctx",
)
def given_profile_with_translate_variables() -> DirectTranslatorContext:
    """Use the default direct translator profile which has translate variables.

    Returns:
        DirectTranslatorContext with profile path.
    """
    ctx = DirectTranslatorContext()
    ctx.profile_path = get_default_agents_dir() / "translate" / "direct_translator.toml"
    return ctx


@then("the profile loads without validation errors")
def then_profile_loads_without_errors(ctx: DirectTranslatorContext) -> None:
    """Assert profile loaded successfully."""
    assert ctx.profile is not None
    assert ctx.error is None
