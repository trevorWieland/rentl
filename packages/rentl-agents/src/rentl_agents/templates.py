"""Template variable system for agent prompts.

This module provides:
- A registry of allowed template variables per context
- Template validation at load time
- Template rendering with variable substitution
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from pydantic import BaseModel, Field

# Template variable pattern: {{variable_name}}
TEMPLATE_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class TemplateValidationError(Exception):
    """Raised when template validation fails.

    Attributes:
        template: The template that failed validation.
        unknown_variables: Set of unknown variable names found.
        allowed_variables: Set of allowed variable names.
    """

    def __init__(
        self,
        message: str,
        template: str,
        unknown_variables: set[str],
        allowed_variables: set[str],
    ) -> None:
        """Initialize the template validation error.

        Args:
            message: Error message.
            template: The template that failed.
            unknown_variables: Variables found but not allowed.
            allowed_variables: Variables that are allowed.
        """
        super().__init__(message)
        self.template = template
        self.unknown_variables = unknown_variables
        self.allowed_variables = allowed_variables


class TemplateRenderError(Exception):
    """Raised when template rendering fails.

    Attributes:
        template: The template that failed to render.
        missing_variables: Set of missing variable names.
    """

    def __init__(
        self,
        message: str,
        template: str,
        missing_variables: set[str],
    ) -> None:
        """Initialize the template render error.

        Args:
            message: Error message.
            template: The template that failed.
            missing_variables: Variables required but not provided.
        """
        super().__init__(message)
        self.template = template
        self.missing_variables = missing_variables


# Allowed variables by layer/context
# Root layer variables (project-level)
ROOT_LAYER_VARIABLES: frozenset[str] = frozenset({
    "game_name",
    "game_synopsis",
})

# Phase layer variables (phase-level)
# These are added to root variables for phase prompts
PHASE_LAYER_VARIABLES: frozenset[str] = frozenset({
    "source_lang",
    "target_lang",
})

# Agent layer variables by phase
# These are added to root + phase variables for agent prompts
CONTEXT_AGENT_VARIABLES: frozenset[str] = frozenset({
    "scene_id",
    "line_count",
    "scene_lines",
    "alignment_feedback",
})

PRETRANSLATION_AGENT_VARIABLES: frozenset[str] = frozenset({
    "scene_id",
    "line_count",
    "source_lines",
    "scene_summary",
    "alignment_feedback",
})

TRANSLATE_AGENT_VARIABLES: frozenset[str] = frozenset({
    "scene_id",
    "line_count",
    "source_lines",
    "annotated_source_lines",
    "scene_summary",
    "pretranslation_notes",
    "glossary_terms",
    "alignment_feedback",
})

QA_AGENT_VARIABLES: frozenset[str] = frozenset({
    "line_id",
    "source_text",
    "translated_text",
    "scene_summary",
    "glossary_terms",
    "style_guide",
    "lines_to_review",
    "alignment_feedback",
})

EDIT_AGENT_VARIABLES: frozenset[str] = frozenset({
    "line_id",
    "source_text",
    "translated_text",
    "qa_issues",
    "scene_summary",
    "alignment_feedback",
})

# Mapping from phase name to agent-specific variables
PHASE_AGENT_VARIABLES: dict[str, frozenset[str]] = {
    "context": CONTEXT_AGENT_VARIABLES,
    "pretranslation": PRETRANSLATION_AGENT_VARIABLES,
    "translate": TRANSLATE_AGENT_VARIABLES,
    "qa": QA_AGENT_VARIABLES,
    "edit": EDIT_AGENT_VARIABLES,
}


def extract_template_variables(template: str) -> set[str]:
    """Extract variable names from a template string.

    Finds all occurrences of {{variable_name}} in the template.

    Args:
        template: Template string to parse.

    Returns:
        Set of variable names found in the template.
    """
    return set(TEMPLATE_VARIABLE_PATTERN.findall(template))


def get_allowed_variables_for_layer(layer: str) -> frozenset[str]:
    """Get allowed variables for a specific layer.

    Args:
        layer: Layer name ('root', 'phase', or phase name for agent layer).

    Returns:
        Set of allowed variable names.

    Raises:
        ValueError: If layer is unknown.
    """
    if layer == "root":
        return ROOT_LAYER_VARIABLES
    if layer == "phase":
        return ROOT_LAYER_VARIABLES | PHASE_LAYER_VARIABLES
    if layer in PHASE_AGENT_VARIABLES:
        return (
            ROOT_LAYER_VARIABLES | PHASE_LAYER_VARIABLES | PHASE_AGENT_VARIABLES[layer]
        )
    raise ValueError(f"Unknown layer: {layer}")


def validate_template(
    template: str,
    allowed_variables: frozenset[str],
    context: str = "template",
) -> None:
    """Validate that a template uses only allowed variables.

    Args:
        template: Template string to validate.
        allowed_variables: Set of allowed variable names.
        context: Context string for error messages.

    Raises:
        TemplateValidationError: If unknown variables are found.
    """
    found_variables = extract_template_variables(template)
    unknown = found_variables - allowed_variables

    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        allowed_list = ", ".join(sorted(allowed_variables))
        raise TemplateValidationError(
            f"Unknown template variables in {context}: {{{unknown_list}}}. "
            f"Allowed: {{{allowed_list}}}",
            template=template,
            unknown_variables=unknown,
            allowed_variables=set(allowed_variables),
        )


def validate_agent_template(
    template: str, phase: str, context: str = "template"
) -> None:
    """Validate an agent template for a specific phase.

    Combines root + phase + agent layer variables.

    Args:
        template: Template string to validate.
        phase: Phase name (context, pretranslation, translate, qa, edit).
        context: Context string for error messages.
    """
    allowed = get_allowed_variables_for_layer(phase)
    validate_template(template, allowed, context)


def render_template(
    template: str,
    variables: Mapping[str, str],
    strict: bool = True,
) -> str:
    """Render a template with variable substitution.

    Args:
        template: Template string with {{variable}} placeholders.
        variables: Mapping of variable names to values.
        strict: If True, raise error for missing variables.

    Returns:
        Rendered template string.

    Raises:
        TemplateRenderError: If strict mode and variables are missing.
    """
    required_variables = extract_template_variables(template)
    provided_variables = set(variables.keys())
    missing = required_variables - provided_variables

    if strict and missing:
        missing_list = ", ".join(sorted(missing))
        raise TemplateRenderError(
            f"Missing template variables: {{{missing_list}}}",
            template=template,
            missing_variables=missing,
        )

    def replace_variable(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    return TEMPLATE_VARIABLE_PATTERN.sub(replace_variable, template)


class TemplateContext(BaseModel):
    """Context for template rendering with layered variables.

    Combines variables from root, phase, and agent layers.
    """

    root_variables: dict[str, str] = Field(
        default_factory=dict, description="Project-level template variables"
    )
    phase_variables: dict[str, str] = Field(
        default_factory=dict, description="Phase-level template variables"
    )
    agent_variables: dict[str, str] = Field(
        default_factory=dict, description="Agent-level template variables"
    )

    def get_all_variables(self) -> dict[str, str]:
        """Get all variables combined (root → phase → agent precedence).

        Returns:
            Dictionary of all variables with later layers overriding earlier.
        """
        combined: dict[str, str] = {}
        combined.update(self.root_variables)
        combined.update(self.phase_variables)
        combined.update(self.agent_variables)
        return combined

    def render(self, template: str, strict: bool = True) -> str:
        """Render a template using all context variables.

        Args:
            template: Template string to render.
            strict: If True, raise error for missing variables.

        Returns:
            Rendered template string.
        """
        return render_template(template, self.get_all_variables(), strict=strict)
