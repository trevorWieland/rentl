"""Load and validate rentl run output files for benchmark comparison."""

from __future__ import annotations

import json

from anyio import Path

from rentl_schemas.io import TranslatedLine
from rentl_schemas.primitives import LineId


class OutputLoadError(Exception):
    """Error loading or validating benchmark output."""


async def load_output(output_path: Path) -> list[TranslatedLine]:
    """Load a rentl run output JSONL file into TranslatedLine format.

    Args:
        output_path: Path to a rentl run output JSONL file

    Returns:
        List of TranslatedLine objects

    Raises:
        OutputLoadError: If the file cannot be read or parsed
    """
    if not await output_path.exists():
        raise OutputLoadError(f"Output file not found: {output_path}")

    if not await output_path.is_file():
        raise OutputLoadError(f"Output path is not a file: {output_path}")

    lines: list[TranslatedLine] = []
    try:
        async with await output_path.open("r", encoding="utf-8") as f:
            line_num = 0
            async for line in f:
                line_num += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    translated_line = TranslatedLine.model_validate(data)
                    lines.append(translated_line)
                except json.JSONDecodeError as e:
                    raise OutputLoadError(
                        f"Invalid JSON at {output_path}:{line_num}: {e}"
                    ) from e
                except Exception as e:
                    raise OutputLoadError(
                        f"Invalid TranslatedLine at {output_path}:{line_num}: {e}"
                    ) from e
    except OutputLoadError:
        raise
    except Exception as e:
        raise OutputLoadError(f"Error reading {output_path}: {e}") from e

    if not lines:
        raise OutputLoadError(f"Output file is empty: {output_path}")

    return lines


def validate_matching_line_ids(
    outputs: dict[str, list[TranslatedLine]],
) -> None:
    """Validate that all candidate outputs cover the same set of line IDs.

    Args:
        outputs: Mapping from candidate name to list of TranslatedLine objects

    Raises:
        OutputLoadError: If line ID sets don't match across candidates
    """
    if not outputs:
        raise OutputLoadError("No outputs provided for validation")

    if len(outputs) < 2:
        raise OutputLoadError(
            f"At least 2 outputs required for comparison, got {len(outputs)}"
        )

    # Extract line ID sets for each candidate
    line_id_sets: dict[str, set[LineId]] = {}
    for candidate_name, lines in outputs.items():
        line_ids = {line.line_id for line in lines}
        if len(line_ids) != len(lines):
            raise OutputLoadError(
                f"Candidate '{candidate_name}' has duplicate line IDs"
            )
        line_id_sets[candidate_name] = line_ids

    # Compare all line ID sets for exact equality
    candidate_names = list(line_id_sets.keys())
    reference_name = candidate_names[0]
    reference_ids = line_id_sets[reference_name]

    for candidate_name in candidate_names[1:]:
        candidate_ids = line_id_sets[candidate_name]
        if candidate_ids != reference_ids:
            missing_from_candidate = reference_ids - candidate_ids
            extra_in_candidate = candidate_ids - reference_ids

            error_parts = [
                f"Line ID mismatch between '{reference_name}' and '{candidate_name}'"
            ]
            if missing_from_candidate:
                missing_sample = sorted(missing_from_candidate)[:5]
                error_parts.append(
                    f"  Missing from '{candidate_name}': {missing_sample}"
                )
                if len(missing_from_candidate) > 5:
                    error_parts.append(
                        f"  ... and {len(missing_from_candidate) - 5} more"
                    )
            if extra_in_candidate:
                extra_sample = sorted(extra_in_candidate)[:5]
                error_parts.append(f"  Extra in '{candidate_name}': {extra_sample}")
                if len(extra_in_candidate) > 5:
                    count = len(extra_in_candidate) - 5
                    error_parts.append(f"  ... and {count} more")

            raise OutputLoadError("\n".join(error_parts))
