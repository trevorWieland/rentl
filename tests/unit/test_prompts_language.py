"""Prompt language expectations for context/detailer subagents."""

from __future__ import annotations

from rentl_agents.subagents.meta_character_curator import SYSTEM_PROMPT as CHARACTER_PROMPT
from rentl_agents.subagents.meta_glossary_curator import SYSTEM_PROMPT as GLOSSARY_PROMPT
from rentl_agents.subagents.meta_location_curator import SYSTEM_PROMPT as LOCATION_PROMPT
from rentl_agents.subagents.route_outline_builder import SYSTEM_PROMPT as ROUTE_PROMPT
from rentl_agents.subagents.scene_summary_detailer import SYSTEM_PROMPT as SCENE_PROMPT


def test_scene_prompt_mentions_source_language() -> None:
    """Scene detailer prompt should emphasize source-language metadata."""
    assert "source language" in SCENE_PROMPT.lower()
    assert "summary" in SCENE_PROMPT.lower()


def test_character_prompt_mentions_source_and_target() -> None:
    """Character detailer should note source language for notes and target for names."""
    prompt = CHARACTER_PROMPT.lower()
    assert "target language" in prompt
    assert "source language" in prompt


def test_location_prompt_mentions_source_language() -> None:
    """Location descriptions should be written in the source language."""
    assert "source language" in LOCATION_PROMPT.lower()


def test_route_prompt_mentions_source_language_synopsis() -> None:
    """Route synopsis should be in source language."""
    assert "source language" in ROUTE_PROMPT.lower()
    assert "synopsis" in ROUTE_PROMPT.lower()


def test_glossary_prompt_notes_language_guidance() -> None:
    """Glossary prompt should guide target rendering and source-language notes."""
    prompt = GLOSSARY_PROMPT.lower()
    assert "target language" in prompt
    assert "source language" in prompt
