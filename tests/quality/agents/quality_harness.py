"""Quality eval harness utilities."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from rentl_agents.providers import detect_provider
from rentl_agents.runtime import ProfileAgentConfig
from rentl_llm.provider_factory import create_model


class QualityModelConfig(BaseModel):
    """Model configuration for quality evals."""

    model_config = ConfigDict(extra="forbid")

    api_key: str = Field(description="API key for the quality eval provider")
    base_url: str = Field(description="Base URL of the quality eval endpoint")
    model_id: str = Field(description="Model identifier for agent under test")
    judge_model_id: str = Field(
        description="Model identifier for LLM-as-judge evaluator"
    )
    judge_base_url: str = Field(description="Base URL for the judge model endpoint")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Quality evals require environment variables. Missing {name}."
        )
    return value


def _load_env_file() -> None:
    """Load environment variables from the repo .env file if present."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def load_quality_model_config() -> QualityModelConfig:
    """Load model configuration from environment variables.

    Returns:
        Quality model configuration.
    """
    _load_env_file()
    api_key = _require_env("RENTL_QUALITY_API_KEY")
    base_url = _require_env("RENTL_QUALITY_BASE_URL")
    model_id = _require_env("RENTL_QUALITY_MODEL")
    judge_model_id = _require_env("RENTL_QUALITY_JUDGE_MODEL")
    judge_base_url = _require_env("RENTL_QUALITY_JUDGE_BASE_URL")

    return QualityModelConfig(
        api_key=api_key,
        base_url=base_url,
        model_id=model_id,
        judge_model_id=judge_model_id,
        judge_base_url=judge_base_url,
    )


def build_profile_config(config: QualityModelConfig) -> ProfileAgentConfig:
    """Build runtime agent config for quality evals.

    Returns:
        Runtime configuration for profile agents.
    """
    return ProfileAgentConfig(
        api_key=config.api_key,
        base_url=config.base_url,
        model_id=config.model_id,
        temperature=0.2,
        timeout_s=15.0,  # Cap per-request to stay within 30s test budget
        max_retries=0,  # No retries — single attempt to avoid timeout amplification
        max_output_retries=2,  # Allow 3 total validation attempts (initial + 2 retries)
        retry_base_delay=1.0,
        end_strategy="exhaustive",
        required_tool_calls=["get_game_info"],
    )


def build_judge_model_and_settings(
    config: QualityModelConfig,
) -> tuple[Model, ModelSettings]:
    """Build a judge model and settings via the centralized factory.

    Returns:
        Tuple of (Model, ModelSettings) for LLM-as-judge evaluators.
    """
    return create_model(
        base_url=config.judge_base_url,
        api_key=config.api_key,
        model_id=config.judge_model_id,
        temperature=0.0,
        max_output_tokens=200,
    )


def verify_openrouter_tool_calling(config: QualityModelConfig) -> tuple[bool, str]:
    """Verify OpenRouter endpoints use correct provider and support tools.

    Args:
        config: Quality model configuration.

    Returns:
        Tuple of (success, message).
    """
    capabilities = detect_provider(config.judge_base_url)

    if "openrouter.ai" in config.judge_base_url:
        if capabilities.name != "OpenRouter":
            return False, f"Expected OpenRouter provider, got {capabilities.name}"
        if not capabilities.supports_tool_calling:
            return False, "OpenRouter should support tool calling"
        return True, f"OpenRouter provider detected correctly with {capabilities.name}"

    return True, f"Non-OpenRouter endpoint: {capabilities.name}"
