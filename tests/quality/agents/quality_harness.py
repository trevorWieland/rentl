"""Quality eval harness utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.settings import ModelSettings

from rentl_agents.runtime import ProfileAgentConfig


@dataclass
class QualityModelConfig:
    """Model configuration for quality evals."""

    api_key: str
    base_url: str
    model_id: str
    judge_model_id: str
    judge_base_url: str


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
        timeout_s=15.0,
        max_retries=0,
        retry_base_delay=1.0,
        output_mode="tool",
        max_output_retries=4,
        max_requests_per_run=10,
        end_strategy="exhaustive",
        required_tool_calls=["get_game_info"],
    )


def build_judge_model(config: QualityModelConfig) -> OpenAIChatModel:
    """Build a judge model instance for LLM-as-judge evaluators.

    Returns:
        Judge model instance.
    """
    if "openrouter.ai" in config.judge_base_url:
        provider = OpenRouterProvider(api_key=config.api_key)
    else:
        provider = OpenAIProvider(
            base_url=config.judge_base_url,
            api_key=config.api_key,
        )
    return OpenAIChatModel(config.judge_model_id, provider=provider)


def build_judge_settings() -> ModelSettings:
    """Build model settings for LLM-as-judge evaluators.

    Returns:
        Judge model settings.
    """
    return ModelSettings(temperature=0.0, max_tokens=200)
