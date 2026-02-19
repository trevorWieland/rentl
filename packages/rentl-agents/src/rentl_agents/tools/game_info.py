"""Game info tool for agent context.

Provides project/game information to agents during execution.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from rentl_schemas.primitives import JsonValue


class ProjectContext(BaseModel):
    """Context about the project being localized.

    This is populated from the run configuration and passed to tools.
    """

    game_name: str = Field(
        default="Unknown Game", description="Name of the game being localized"
    )
    synopsis: str | None = Field(default=None, description="Brief synopsis of the game")
    source_language: str = Field(
        default="ja", description="ISO language code for the source language"
    )
    target_languages: list[str] = Field(
        default_factory=list, description="ISO language codes for target languages"
    )


class GameInfoTool:
    """Tool that returns project/game information.

    This tool provides context about the game being localized,
    including name, synopsis, and language configuration.
    """

    def __init__(self, context: ProjectContext | None = None) -> None:
        """Initialize the game info tool.

        Args:
            context: Project context to return. Defaults to empty context.
        """
        self._context = context or ProjectContext()

    @property
    def name(self) -> str:
        """Tool identifier."""
        return "get_game_info"

    @property
    def description(self) -> str:
        """Tool description for LLM."""
        return (
            "Get information about the game being localized. "
            "Returns game name, synopsis, source language, and target languages."
        )

    def execute(self, **kwargs: JsonValue) -> dict[str, JsonValue]:
        """Execute the tool.

        Args:
            **kwargs: Unused - this tool takes no arguments.

        Returns:
            Dictionary with game information.
        """
        target_languages: list[JsonValue] = list(self._context.target_languages)
        return {
            "game_name": self._context.game_name,
            "synopsis": self._context.synopsis or "No synopsis provided",
            "source_language": self._context.source_language,
            "target_languages": target_languages,
        }

    def update_context(self, context: ProjectContext) -> None:
        """Update the project context.

        Args:
            context: New project context.
        """
        self._context = context
