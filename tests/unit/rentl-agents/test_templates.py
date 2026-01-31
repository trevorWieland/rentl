"""Unit tests for template variable system."""

from __future__ import annotations

import pytest

from rentl_agents.templates import (
    TemplateContext,
    TemplateRenderError,
    TemplateValidationError,
    extract_template_variables,
    get_allowed_variables_for_layer,
    render_template,
    validate_agent_template,
    validate_template,
)


class TestExtractTemplateVariables:
    """Test cases for extract_template_variables function."""

    def test_extract_single_variable(self) -> None:
        """Test extracting a single variable from template."""
        template = "Hello {{name}}"
        variables = extract_template_variables(template)

        assert variables == {"name"}

    def test_extract_multiple_variables(self) -> None:
        """Test extracting multiple variables from template."""
        template = "{{greeting}} {{name}}, welcome to {{place}}"
        variables = extract_template_variables(template)

        assert variables == {"greeting", "name", "place"}

    def test_extract_no_variables(self) -> None:
        """Test extracting from template with no variables."""
        template = "Plain text with no variables"
        variables = extract_template_variables(template)

        assert variables == set()

    def test_extract_duplicate_variables(self) -> None:
        """Test extracting returns unique set."""
        template = "{{name}} and {{name}} again"
        variables = extract_template_variables(template)

        assert variables == {"name"}

    def test_extract_with_whitespace_in_braces(self) -> None:
        """Test variable extraction ignores malformed braces."""
        template = "{{ name }}"  # Has spaces
        variables = extract_template_variables(template)

        # Standard regex won't match spaces inside braces
        assert "name" not in variables


class TestValidateTemplate:
    """Test cases for validate_template function."""

    def test_valid_template(self) -> None:
        """Test validation passes for valid template."""
        template = "Hello {{game_name}}"
        allowed = frozenset({"game_name", "game_synopsis"})

        # Should not raise
        validate_template(template, allowed)

    def test_invalid_variable_raises_error(self) -> None:
        """Test validation raises for unknown variable."""
        template = "Hello {{unknown_var}}"
        allowed = frozenset({"game_name"})

        with pytest.raises(TemplateValidationError) as exc_info:
            validate_template(template, allowed)

        assert "unknown_var" in str(exc_info.value)
        assert exc_info.value.unknown_variables == {"unknown_var"}

    def test_multiple_invalid_variables(self) -> None:
        """Test validation reports all unknown variables."""
        template = "{{foo}} and {{bar}}"
        allowed = frozenset({"game_name"})

        with pytest.raises(TemplateValidationError) as exc_info:
            validate_template(template, allowed)

        assert exc_info.value.unknown_variables == {"foo", "bar"}

    def test_empty_template(self) -> None:
        """Test validation passes for empty template."""
        validate_template("", frozenset({"game_name"}))

    def test_context_in_error_message(self) -> None:
        """Test context appears in error message."""
        template = "{{unknown}}"

        with pytest.raises(TemplateValidationError) as exc_info:
            validate_template(template, frozenset(), context="my custom context")

        assert "my custom context" in str(exc_info.value)


class TestGetAllowedVariablesForLayer:
    """Test cases for get_allowed_variables_for_layer function."""

    def test_root_layer(self) -> None:
        """Test root layer variables."""
        allowed = get_allowed_variables_for_layer("root")

        assert "game_name" in allowed
        assert "game_synopsis" in allowed

    def test_context_phase(self) -> None:
        """Test context phase layer variables."""
        allowed = get_allowed_variables_for_layer("context")

        # Should include root + phase + agent-specific
        assert "game_name" in allowed
        assert "source_lang" in allowed
        assert "scene_id" in allowed
        assert "scene_lines" in allowed

    def test_translate_phase(self) -> None:
        """Test translate phase layer variables."""
        allowed = get_allowed_variables_for_layer("translate")

        assert "game_name" in allowed
        assert "source_lang" in allowed
        assert "target_lang" in allowed
        assert "source_lines" in allowed  # Translate uses source_lines, not source_text

    def test_unknown_phase_raises(self) -> None:
        """Test unknown phase raises ValueError."""
        with pytest.raises(ValueError):
            get_allowed_variables_for_layer("unknown_phase")


class TestValidateAgentTemplate:
    """Test cases for validate_agent_template function."""

    def test_valid_context_template(self) -> None:
        """Test validation of valid context phase template."""
        template = "Scene: {{scene_id}}\n{{scene_lines}}"

        # Should not raise
        validate_agent_template(template, "context")

    def test_valid_translate_template(self) -> None:
        """Test validation of valid translate phase template."""
        template = "Translate to {{target_lang}}:\n{{source_lines}}"

        # Should not raise
        validate_agent_template(template, "translate")

    def test_invalid_variable_for_phase(self) -> None:
        """Test validation fails for unknown variable."""
        template = "{{completely_unknown_var}}"  # Not in any phase

        with pytest.raises(TemplateValidationError):
            validate_agent_template(template, "context")


class TestRenderTemplate:
    """Test cases for render_template function."""

    def test_render_single_variable(self) -> None:
        """Test rendering template with single variable."""
        template = "Hello {{name}}"
        result = render_template(template, {"name": "World"})

        assert result == "Hello World"

    def test_render_multiple_variables(self) -> None:
        """Test rendering template with multiple variables."""
        template = "{{greeting}} {{name}}"
        result = render_template(
            template,
            {"greeting": "Hello", "name": "World"},
        )

        assert result == "Hello World"

    def test_render_preserves_unmatched_in_non_strict(self) -> None:
        """Test non-strict rendering preserves unmatched variables."""
        template = "{{greeting}} {{name}}"
        result = render_template(
            template,
            {"greeting": "Hello"},
            strict=False,
        )

        assert result == "Hello {{name}}"

    def test_render_strict_raises_for_missing(self) -> None:
        """Test strict rendering raises for missing variables."""
        template = "{{greeting}} {{name}}"

        with pytest.raises(TemplateRenderError) as exc_info:
            render_template(template, {"greeting": "Hello"}, strict=True)

        assert "name" in str(exc_info.value)

    def test_render_empty_template(self) -> None:
        """Test rendering empty template."""
        result = render_template("", {"name": "World"})

        assert result == ""

    def test_render_no_variables(self) -> None:
        """Test rendering template with no variables."""
        result = render_template("Plain text", {})

        assert result == "Plain text"


class TestTemplateContext:
    """Test cases for TemplateContext class."""

    def test_create_empty_context(self) -> None:
        """Test creating empty template context."""
        ctx = TemplateContext()

        assert ctx.root_variables == {}
        assert ctx.phase_variables == {}
        assert ctx.agent_variables == {}

    def test_create_context_with_values(self) -> None:
        """Test creating context with values."""
        ctx = TemplateContext(
            root_variables={"game_name": "Test Game", "game_synopsis": "A test game"},
            phase_variables={"source_lang": "Japanese"},
            agent_variables={"scene_id": "scene_001", "scene_lines": "Line 1\nLine 2"},
        )

        assert ctx.root_variables["game_name"] == "Test Game"
        assert ctx.agent_variables["scene_id"] == "scene_001"

    def test_get_all_variables(self) -> None:
        """Test get_all_variables combines all layers."""
        ctx = TemplateContext(
            root_variables={"game_name": "Test Game"},
            phase_variables={"source_lang": "Japanese"},
            agent_variables={"scene_id": "scene_001"},
        )

        all_vars = ctx.get_all_variables()

        assert all_vars["game_name"] == "Test Game"
        assert all_vars["source_lang"] == "Japanese"
        assert all_vars["scene_id"] == "scene_001"

    def test_layer_precedence(self) -> None:
        """Test later layers override earlier ones."""
        ctx = TemplateContext(
            root_variables={"value": "root"},
            phase_variables={"value": "phase"},
            agent_variables={"value": "agent"},
        )

        all_vars = ctx.get_all_variables()

        assert all_vars["value"] == "agent"  # Agent takes precedence

    def test_render_template(self) -> None:
        """Test rendering template with context."""
        ctx = TemplateContext(
            root_variables={"game_name": "Test Game"},
            agent_variables={"scene_id": "scene_001"},
        )

        result = ctx.render("{{game_name}}: {{scene_id}}")

        assert result == "Test Game: scene_001"
