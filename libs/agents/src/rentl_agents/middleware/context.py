"""Middleware helpers for injecting shared ProjectContext."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime
from rentl_core.context.project import ProjectContext


@dataclass
class AgentContext:
    """Runtime context shared across subagents."""

    project_context: ProjectContext


class ContextInjectionMiddleware(AgentMiddleware[AgentState, AgentContext]):
    """Injects shared ProjectContext into the agent runtime."""

    def __init__(self, project_context: ProjectContext) -> None:
        """Store the shared project context for later injection."""
        self.project_context = project_context

    def before_agent(self, state: AgentState, runtime: Runtime[AgentContext]) -> dict[str, Any]:
        """Attach context before sync agent execution.

        Returns:
            dict[str, Any]: Empty metadata for middleware chaining.
        """
        runtime.context.project_context = self.project_context
        return {}

    async def abefore_agent(self, state: AgentState, runtime: Runtime[AgentContext]) -> dict[str, Any]:
        """Attach context before async agent execution.

        Returns:
            dict[str, Any]: Empty metadata for middleware chaining.
        """
        runtime.context.project_context = self.project_context
        return {}
