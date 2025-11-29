"""Integration tests for editor report output and SQLite checkpointer."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from rentl_agents.subagents.consistency_checks import ConsistencyCheckResult
from rentl_agents.subagents.style_checks import StyleCheckResult
from rentl_agents.subagents.translation_reviewer import TranslationReviewResult
from rentl_cli.utils.baseline import write_baseline
from rentl_core.context.project import load_project_context
from rentl_core.model.line import TranslatedLine
from rentl_pipelines.flows.editor import EditorResult, _run_editor_async


@pytest.fixture
def anyio_backend() -> str:
    """Force asyncio backend.

    Returns:
        str: The backend name.
    """
    return "asyncio"


async def _seed_translations(project_path: Path) -> None:
    """Write simple translations for all scenes to enable editing tests."""
    context = await load_project_context(project_path)
    for sid, scene in context.scenes.items():
        lines = await context.load_scene_lines(sid)
        for line in lines:
            translation = TranslatedLine.from_source(line, f"tgt-{line.id}", text_tgt_origin="agent:test")
            await context.record_translation(scene.id, translation, allow_overwrite=True)


@pytest.mark.anyio
async def test_editor_writes_report_and_uses_sqlite_checkpointer(tmp_path: Path) -> None:
    """Editor pipeline should write a report and accept a SQLite checkpointer."""
    await write_baseline(tmp_path)
    await _seed_translations(tmp_path)
    report_path = tmp_path / "output" / "reports" / "editor_report_test.json"
    db_path = tmp_path / ".rentl" / "checkpoints.db"
    await anyio.Path(db_path.parent).mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:

        async def style_ok(context: object, scene_id: str, **_: object) -> StyleCheckResult:
            await anyio.sleep(0.001)
            return StyleCheckResult(scene_id=scene_id, checks_recorded=1)

        async def consistency_ok(context: object, scene_id: str, **_: object) -> ConsistencyCheckResult:
            await anyio.sleep(0.001)
            return ConsistencyCheckResult(scene_id=scene_id, checks_recorded=1)

        async def review_ok(context: object, scene_id: str, **_: object) -> TranslationReviewResult:
            await anyio.sleep(0.001)
            return TranslationReviewResult(scene_id=scene_id, checks_recorded=1)

        result: EditorResult = await _run_editor_async(
            tmp_path,
            concurrency=2,
            checkpointer=checkpointer,
            report_path=report_path,
            style_runner=style_ok,
            consistency_runner=consistency_ok,
            review_runner=review_ok,
        )

        assert report_path.exists(), "Report file should be written."
        assert result.scenes_checked > 0
        assert result.scenes_skipped == 0
        assert result.translation_progress >= 0.0
        assert result.editing_progress >= 0.0
        assert result.report_path == str(report_path)
        assert isinstance(result.route_issue_counts, dict)

        # Report should contain summary and per-scene findings.
        import orjson

        payload = orjson.loads(report_path.read_bytes())
        assert "summary" in payload
        assert payload["summary"]["translation_progress_pct"] >= 0.0
        assert payload["summary"]["editing_progress_pct"] >= 0.0
        assert payload["scenes"], "Report should include per-scene findings"
        assert "top_issues" in payload
        assert "route_top_issues" in payload
