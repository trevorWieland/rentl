"""Async writers for rentl translation outputs and QA reports."""

from __future__ import annotations

from pathlib import Path

import anyio
import orjson

from rentl_core.model.line import TranslatedLine


async def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write newline-delimited JSON records to path.

    Args:
        path: Path to output file.
        records: List of dictionaries to serialize as JSONL.
    """
    async with await anyio.open_file(path, "wb") as stream:
        for record in records:
            line = orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE)
            await stream.write(line)


async def write_translation(path: Path, lines: list[TranslatedLine]) -> None:
    """Write translated lines to a JSONL file.

    Args:
        path: Output path for translation file (e.g., output/translations/scene_c_00.jsonl).
        lines: List of translated lines to write.
    """
    # Ensure parent directory exists
    parent = path.parent
    await anyio.Path(parent).mkdir(parents=True, exist_ok=True)

    # Serialize all lines (this also validates provenance via pydantic validators)
    records = [line.model_dump(mode="json", exclude_none=False) for line in lines]

    # Write to file
    await _write_jsonl(path, records)


async def write_qa_report(path: Path, translations: list[TranslatedLine], scene_id: str) -> None:
    """Generate and write a QA report from translation check results.

    Args:
        path: Output path for QA report (e.g., output/reports/scene_c_00_qa.txt).
        translations: List of translated lines with QA check results.
        scene_id: Scene identifier for the report header.
    """
    # Ensure parent directory exists
    parent = path.parent
    await anyio.Path(parent).mkdir(parents=True, exist_ok=True)

    # Build report content
    lines: list[str] = []
    lines.append(f"QA Report for Scene: {scene_id}")
    lines.append("=" * 80)
    lines.append("")

    # Summary statistics
    total_lines = len(translations)
    lines_with_checks = sum(1 for t in translations if t.meta.checks)
    total_checks = sum(len(t.meta.checks) for t in translations)
    failed_checks = sum(1 for t in translations for check in t.meta.checks.values() if not check[0])

    lines.append(f"Total Lines: {total_lines}")
    lines.append(f"Lines with QA Checks: {lines_with_checks}")
    lines.append(f"Total Checks Run: {total_checks}")
    lines.append(f"Failed Checks: {failed_checks}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("")

    # Detail section - only show lines with failed checks
    if failed_checks > 0:
        lines.append("FAILED CHECKS")
        lines.append("-" * 80)
        lines.append("")

        for translation in translations:
            if not translation.meta.checks:
                continue

            # Check if this line has any failures
            has_failures = any(not check[0] for check in translation.meta.checks.values())
            if not has_failures:
                continue

            lines.append(f"Line ID: {translation.id}")
            lines.append(f"Source: {translation.text_src}")
            lines.append(f"Translation: {translation.text_tgt}")
            lines.append("")

            for check_name, (passed, note) in translation.meta.checks.items():
                if not passed:
                    status = "FAIL"
                    lines.append(f"  [{status}] {check_name}")
                    if note:
                        lines.append(f"       {note}")

            lines.append("")
            lines.append("-" * 80)
            lines.append("")
    else:
        lines.append("All checks passed!")
        lines.append("")

    # Write report
    content = "\n".join(lines)
    async with await anyio.open_file(path, "w", encoding="utf-8") as stream:
        await stream.write(content)
