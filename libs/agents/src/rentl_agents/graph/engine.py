"""Utilities for constructing DeepAgents graphs.

This module imports and re-exports subagent functions for convenience.
"""

from __future__ import annotations

from rentl_agents.subagents.character_detailer import CharacterDetailResult, detail_character
from rentl_agents.subagents.glossary_curator import GlossaryDetailResult, detail_glossary
from rentl_agents.subagents.location_detailer import LocationDetailResult, detail_location
from rentl_agents.subagents.route_detailer import RouteDetailResult, detail_route
from rentl_agents.subagents.scene_detailer import SceneDetailResult, detail_scene
from rentl_agents.subagents.translate_scene import SceneTranslationResult, translate_scene

__all__ = [
    "CharacterDetailResult",
    "GlossaryDetailResult",
    "LocationDetailResult",
    "RouteDetailResult",
    "SceneDetailResult",
    "SceneTranslationResult",
    "detail_character",
    "detail_glossary",
    "detail_location",
    "detail_route",
    "detail_scene",
    "translate_scene",
]
