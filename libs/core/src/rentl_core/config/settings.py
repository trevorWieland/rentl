"""Runtime settings and environment loading utilities."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

_ENV_PATH = Path(".env")


class _Settings(BaseSettings):
    """Base settings loaded from environment variables or .env files."""

    openai_url: str = Field(..., alias="OPENAI_URL")
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    llm_model: str = Field(..., alias="LLM_MODEL")
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")

    class Config:
        env_file = _ENV_PATH
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> _Settings:
    """Return cached settings loaded from the environment."""
    return _Settings()
