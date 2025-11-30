"""Middleware helpers for injecting shared ProjectContext."""

from __future__ import annotations

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict, Field
from rentl_core.context.project import ProjectContext


class AgentContext(BaseModel):
    """Runtime context shared across subagents."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    project_context: ProjectContext = Field(description="Shared ProjectContext for subagents.")


class ContextInjectionMiddleware(AgentMiddleware[AgentState, AgentContext]):
    """Injects shared ProjectContext into the agent runtime."""

    def __init__(self, project_context: ProjectContext) -> None:
        """Store the shared project context for later injection."""
        self.project_context = project_context

    def before_agent(self, state: AgentState, runtime: Runtime[AgentContext]) -> dict[str, AgentContext]:
        """Attach context before sync agent execution.

        Returns:
            dict[str, AgentContext]: Empty metadata for middleware chaining.
        """
        return {"context": AgentContext(project_context=self.project_context)}

    async def abefore_agent(self, state: AgentState, runtime: Runtime[AgentContext]) -> dict[str, AgentContext]:
        """Attach context before async agent execution.

        Returns:
            dict[str, AgentContext]: Empty metadata for middleware chaining.
        """
        return {"context": AgentContext(project_context=self.project_context)}


class DeepContextMiddleware(AgentMiddleware[AgentState, AgentContext]):
    """Inject shared ProjectContext for coordinator-style agents (legacy)."""

    def __init__(self, project_context: ProjectContext) -> None:
        """Store the shared project context for later injection."""
        self.project_context = project_context

    def before_agent(self, state: AgentState, runtime: Runtime[AgentContext]) -> dict[str, AgentContext]:
        """Attach context before sync agent execution.

        Returns:
            dict[str, AgentContext]: Empty metadata for middleware chaining.
        """
        return {"context": AgentContext(project_context=self.project_context)}

    async def abefore_agent(self, state: AgentState, runtime: Runtime[AgentContext]) -> dict[str, AgentContext]:
        """Attach context before async agent execution.

        Returns:
            dict[str, AgentContext]: Empty metadata for middleware chaining.
        """
        return {"context": AgentContext(project_context=self.project_context)}
