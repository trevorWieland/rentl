"""Pretranslation phase agent utilities.

This module provides:
- Line chunking for batch processing
- Line formatting for prompt injection
- Scene summary lookup for context
- Annotation conversion and merging
"""

from rentl_agents.pretranslation.lines import (
    chunk_lines,
    format_lines_for_prompt,
    get_scene_summary_for_lines,
    idiom_to_annotation,
    merge_idiom_annotations,
)

__all__ = [
    "chunk_lines",
    "format_lines_for_prompt",
    "get_scene_summary_for_lines",
    "idiom_to_annotation",
    "merge_idiom_annotations",
]
