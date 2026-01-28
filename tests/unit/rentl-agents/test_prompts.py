"""Unit tests for prompt templates."""

from __future__ import annotations

import pytest

from rentl_agents.prompts import PromptRenderer, PromptTemplate


class TestPromptTemplate:
    """Test cases for PromptTemplate class."""

    def test_create_valid_template(self) -> None:
        """Test creating a valid prompt template."""
        template = PromptTemplate(
            name="translate",
            template="Translate {{text}} to {{target}}",
            variables={"text": "str", "target": "str"},
        )

        assert template.name == "translate"
        assert template.template == "Translate {{text}} to {{target}}"
        assert template.variables == {"text": "str", "target": "str"}
        assert template.version == "1.0.0"

    def test_create_template_with_defaults(self) -> None:
        """Test creating a template with default values."""
        template = PromptTemplate(
            name="translate",
            template="Translate {{text}} to {{target}} using {{style}}",
            variables={"text": "str", "target": "str", "style": "str"},
            default_values={"style": "formal"},
        )

        assert template.default_values == {"style": "formal"}

    def test_create_template_with_invalid_default_value(self) -> None:
        """Test creating template raises error for unknown variable in defaults."""
        with pytest.raises(ValueError, match="Default value for unknown variable"):
            PromptTemplate(
                name="translate",
                template="Translate {{text}}",
                variables={"text": "str"},
                default_values={"target": "en"},
            )

    def test_create_template_with_empty_name(self) -> None:
        """Test creating template raises error for empty name."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="name"):
            PromptTemplate(
                name="",
                template="Translate {{text}}",
                variables={"text": "str"},
            )

    def test_create_template_with_empty_template_string(self) -> None:
        """Test creating template raises error for empty template string."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="template"):
            PromptTemplate(
                name="translate",
                template="",
                variables={"text": "str"},
            )


class TestPromptRenderer:
    """Test cases for PromptRenderer class."""

    def test_extract_variables_from_template(self) -> None:
        """Test extracting variables from template."""
        renderer = PromptRenderer()
        template = "Translate {{text}} from {{source}} to {{target}}"

        variables = renderer.extract_variables(template)

        assert variables == {"text", "source", "target"}

    def test_extract_variables_from_template_without_placeholders(self) -> None:
        """Test extracting variables from template without placeholders."""
        renderer = PromptRenderer()
        template = "Translate this text"

        variables = renderer.extract_variables(template)

        assert variables == set()

    def test_render_template_with_full_context(self) -> None:
        """Test rendering template with all variables provided."""
        renderer = PromptRenderer()
        template = "Translate {{text}} from {{source}} to {{target}}"
        context = {"text": "Hello", "source": "en", "target": "ja"}

        rendered = renderer.render_template(template, context)

        assert rendered == "Translate Hello from en to ja"

    def test_render_template_with_partial_context(self) -> None:
        """Test rendering template with missing variable raises error in strict mode."""
        renderer = PromptRenderer()
        template = "Translate {{text}} from {{source}} to {{target}}"
        context = {"text": "Hello", "source": "en"}

        with pytest.raises(ValueError, match="Missing required variables"):
            renderer.render_template(template, context, strict=True)

    def test_render_template_with_partial_context_non_strict(self) -> None:
        """Test rendering template with missing variable in non-strict mode."""
        renderer = PromptRenderer()
        template = "Translate {{text}} from {{source}} to {{target}}"
        context = {"text": "Hello", "source": "en"}

        rendered = renderer.render_template(template, context, strict=False)

        assert rendered == "Translate Hello from en to {{target}}"

    def test_render_template_with_none_value_strict(self) -> None:
        """Test rendering template with None value in strict mode."""
        renderer = PromptRenderer()
        template = "Translate {{text}} to {{target}}"
        context = {"text": "Hello", "target": None}

        with pytest.raises(ValueError, match="Variable target is None"):
            renderer.render_template(template, context, strict=True)

    def test_render_template_with_none_value_non_strict(self) -> None:
        """Test rendering template with None value in non-strict mode."""
        renderer = PromptRenderer()
        template = "Translate {{text}} to {{target}}"
        context = {"text": "Hello", "target": None}

        rendered = renderer.render_template(template, context, strict=False)

        assert rendered == "Translate Hello to "

    def test_render_template_with_numeric_values(self) -> None:
        """Test rendering template with numeric context values."""
        renderer = PromptRenderer()
        template = "Score: {{score}} / {{max_score}}"
        context = {"score": 95, "max_score": 100}

        rendered = renderer.render_template(template, context)

        assert rendered == "Score: 95 / 100"

    def test_render_template_with_list_values(self) -> None:
        """Test rendering template with list context values."""
        renderer = PromptRenderer()
        template = "Items: {{items}}"
        context = {"items": ["apple", "banana", "cherry"]}

        rendered = renderer.render_template(template, context)

        assert rendered == "Items: ['apple', 'banana', 'cherry']"

    def test_render_template_object_with_defaults(self) -> None:
        """Test rendering PromptTemplate object with default values."""
        renderer = PromptRenderer()
        template = PromptTemplate(
            name="translate",
            template="Translate {{text}} to {{target}} using {{style}}",
            variables={"text": "str", "target": "str", "style": "str"},
            default_values={"style": "formal"},
        )
        context = {"text": "Hello", "target": "ja"}

        rendered = renderer.render_template_object(template, context)

        assert rendered == "Translate Hello to ja using formal"

    def test_render_template_caching(self) -> None:
        """Test that variable extraction is cached."""
        renderer = PromptRenderer()
        template = "Translate {{text}} to {{target}}"

        variables1 = renderer.extract_variables(template)
        variables2 = renderer.extract_variables(template)

        assert variables1 == variables2
        # Results should be equal sets but may be different object instances

    def test_build_context_with_optional_fields(self) -> None:
        """Test building context with optional injected fields."""
        renderer = PromptRenderer()
        base_context = {"text": "Hello", "target": "ja"}

        context = renderer.build_context(
            base_context,
            project_context="Game translation",
            style_guide="Use formal tone",
            glossary=[{"term": "hello", "translation": "こんにちは"}],
        )

        assert context["text"] == "Hello"
        assert context["target"] == "ja"
        assert context["project_context"] == "Game translation"
        assert context["style_guide"] == "Use formal tone"
        assert context["glossary"] == [{"term": "hello", "translation": "こんにちは"}]

    def test_build_context_without_optional_fields(self) -> None:
        """Test building context without optional injected fields."""
        renderer = PromptRenderer()
        base_context = {"text": "Hello", "target": "ja"}

        context = renderer.build_context(base_context)

        assert context == {"text": "Hello", "target": "ja"}

    def test_build_context_overwrites_base(self) -> None:
        """Test that injected fields do not overwrite base context."""
        renderer = PromptRenderer()
        base_context = {
            "text": "Hello",
            "project_context": "Original context",
        }

        context = renderer.build_context(
            base_context,
            project_context="Injected context",
        )

        assert context["text"] == "Hello"
        assert context["project_context"] == "Injected context"
