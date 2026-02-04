"""Prompt template system for variable substitution."""

from __future__ import annotations

import re
from functools import cache

from pydantic import Field, field_validator, model_validator

from rentl_schemas.base import BaseSchema
from rentl_schemas.primitives import JsonValue

# Module-level cached function to avoid memory leak from lru_cache on methods
_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


@cache
def _extract_variables_cached(template: str) -> frozenset[str]:
    """Extract variable names from template (cached).

    Args:
        template: Template string.

    Returns:
        Frozenset of variable names.
    """
    return frozenset(_VARIABLE_PATTERN.findall(template))


class PromptTemplate(BaseSchema):
    """Prompt template with variable substitution.

    Templates use `{{variable}}` syntax for substitution.

    Args:
        name: Template name for identification.
        template: Template string with variable placeholders.
        variables: Variable definitions with types and descriptions.
        default_values: Default values for optional variables.
        version: Template version for tracking changes.
        description: Template description.
    """

    name: str = Field(..., min_length=1, description="Template name")
    template: str = Field(
        ..., min_length=1, description="Template string with {{variable}} placeholders"
    )
    variables: dict[str, str] = Field(
        default_factory=dict, description="Variable type definitions"
    )
    default_values: dict[str, JsonValue] = Field(
        default_factory=dict, description="Default values for optional variables"
    )
    version: str = Field(default="1.0.0", description="Template version")
    description: str | None = Field(None, description="Template description")

    @field_validator("template")
    @classmethod
    def validate_template(cls, v: str) -> str:
        """Validate template syntax.

        Args:
            v: Template string to validate.

        Returns:
            Validated template string.

        Raises:
            ValueError: If template syntax is invalid.
        """
        try:
            re.findall(r"\{\{(\w+)\}\}", v)
        except re.error as exc:
            raise ValueError(f"Invalid template syntax: {exc}") from exc
        return v

    @model_validator(mode="after")
    def validate_default_values(self) -> PromptTemplate:
        """Validate default values match variables.

        Returns:
            Validated prompt template.

        Raises:
            ValueError: If default value key is not in variables.
        """
        for key in self.default_values:
            if key not in self.variables:
                raise ValueError(f"Default value for unknown variable: {key}")
        return self


class PromptRenderer:
    """Renderer for prompt templates with variable substitution.

    This renderer provides:
    - Variable substitution from context data
    - Type conversion and validation
    - Template caching for performance
    - Error handling for missing variables

    Usage:
        renderer = PromptRenderer()
        template = "Translate {{text}} from {{source}} to {{target}}"
        context = {"text": "Hello", "source": "en", "target": "ja"}
        rendered = renderer.render_template(template, context)
    """

    def __init__(self) -> None:
        """Initialize the prompt renderer."""
        self._variable_pattern = re.compile(r"\{\{(\w+)\}\}")

    def extract_variables(self, template: str) -> set[str]:
        """Extract variable names from template.

        Args:
            template: Template string.

        Returns:
            Set of variable names.
        """
        return set(_extract_variables_cached(template))

    def render_template(
        self,
        template: str,
        context: dict[str, JsonValue],
        strict: bool = True,
    ) -> str:
        """Render template with variable substitution.

        Args:
            template: Template string with {{variable}} placeholders.
            context: Context data for variable substitution.
            strict: If True, raise error for missing variables.

        Returns:
            Rendered template string.

        Raises:
            ValueError: If required variable is missing and strict is True.
        """
        required_vars = self.extract_variables(template)
        missing_vars = required_vars - set(context.keys())

        if missing_vars and strict:
            raise ValueError(f"Missing required variables: {missing_vars}")

        result = template

        for var_name in required_vars:
            if var_name not in context:
                continue

            placeholder = f"{{{{{var_name}}}}}"
            value = context[var_name]

            if value is None:
                if strict:
                    raise ValueError(f"Variable {var_name} is None")
                else:
                    result = result.replace(placeholder, "")
                continue

            result = result.replace(placeholder, str(value))

        return result

    def render_template_object(
        self,
        prompt_template: PromptTemplate,
        context: dict[str, JsonValue],
    ) -> str:
        """Render a PromptTemplate object with context.

        Args:
            prompt_template: PromptTemplate object to render.
            context: Context data for variable substitution.

        Returns:
            Rendered template string.
        """
        merged_context = {**prompt_template.default_values, **context}
        return self.render_template(
            prompt_template.template,
            merged_context,
            strict=True,
        )

    def build_context(
        self,
        base_context: dict[str, JsonValue],
        project_context: str | None = None,
        style_guide: str | None = None,
        glossary: list[JsonValue] | None = None,
    ) -> dict[str, JsonValue]:
        """Build context with optional injected fields.

        Args:
            base_context: Base context data.
            project_context: Optional project-level context string.
            style_guide: Optional style guide content.
            glossary: Optional glossary terms list.

        Returns:
            Merged context dictionary.
        """
        context = dict(base_context)

        if project_context is not None:
            context["project_context"] = project_context

        if style_guide is not None:
            context["style_guide"] = style_guide

        if glossary is not None:
            context["glossary"] = glossary

        return context
