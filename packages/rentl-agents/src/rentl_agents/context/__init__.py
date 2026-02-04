"""Context phase agent utilities.

This module provides:
- Scene validation for the scene summarizer
- Scene grouping utilities for sharding
- Output merging for context phase results
"""

from rentl_agents.context.scene import (
    SceneValidationError,
    format_scene_lines,
    group_lines_by_scene,
    merge_scene_summaries,
    validate_scene_input,
)

__all__ = [
    "SceneValidationError",
    "format_scene_lines",
    "group_lines_by_scene",
    "merge_scene_summaries",
    "validate_scene_input",
]
