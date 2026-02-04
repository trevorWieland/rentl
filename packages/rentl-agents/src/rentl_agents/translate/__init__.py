"""Translate phase utilities.

This package provides utilities for the translate phase, including:
- Line chunking and formatting
- Scene summary and annotation lookup
- Translation result conversion
"""

from __future__ import annotations

from rentl_agents.translate.lines import (
    chunk_lines,
    format_annotated_lines_for_prompt,
    format_glossary_terms,
    format_lines_for_prompt,
    format_pretranslation_annotations,
    get_scene_summary_for_lines,
    merge_translated_lines,
    translation_result_to_lines,
)

__all__ = [
    "chunk_lines",
    "format_annotated_lines_for_prompt",
    "format_glossary_terms",
    "format_lines_for_prompt",
    "format_pretranslation_annotations",
    "get_scene_summary_for_lines",
    "merge_translated_lines",
    "translation_result_to_lines",
]
