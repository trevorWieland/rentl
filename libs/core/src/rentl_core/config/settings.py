"""Runtime settings and environment loading utilities."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(".env")


class _Settings(BaseSettings):
    """Base settings loaded from environment variables or .env files."""

    model_config = SettingsConfigDict(env_file=_ENV_PATH, env_file_encoding="utf-8", case_sensitive=False)

    # Primary LLM (agentic reasoning and orchestration)
    openai_url: str = Field(..., alias="OPENAI_URL")
    openai_api_key: SecretStr = Field(..., alias="OPENAI_API_KEY")
    llm_model: str = Field(..., alias="LLM_MODEL")

    # Machine Translation (MTL) backend (optional, for specialized translation)
    mtl_url: str | None = Field(default=None, alias="MTL_URL")
    mtl_api_key: SecretStr | None = Field(default=None, alias="MTL_API_KEY")
    mtl_model: str | None = Field(default=None, alias="MTL_MODEL")
    mtl_system_prompt: str | None = Field(default=None, alias="MTL_SYSTEM_PROMPT")

    # Optional services
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> _Settings:
    """Return cached settings loaded from the environment."""
    return _Settings()
