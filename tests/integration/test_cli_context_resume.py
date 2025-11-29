"""CLI-level resume and thread-id round-trip for context pipeline."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import anyio
import pytest
from rentl_cli.main import app
from rentl_cli.utils.status_snapshot import load_phase_status
from rentl_core.context.project import ProjectContext, load_project_context
from typer.testing import CliRunner

runner = CliRunner()


async def _detail_scene_stub(context: ProjectContext, scene_id: str, **_: object) -> None:
    """Lightweight scene detailer stub to avoid LLMs."""
    await context.set_scene_summary(scene_id, f"summary-{scene_id}", "agent:test")
    await context.set_scene_tags(scene_id, ["tag-a", "tag-b"], "agent:test")
    await context.set_scene_characters(scene_id, ["mc"], "agent:test")
    await context.set_scene_locations(scene_id, ["classroom"], "agent:test")


async def _detail_character_stub(context: ProjectContext, character_id: str, **_: object) -> None:
    """Lightweight character detailer stub."""
    origin = f"agent:test:{date.today().isoformat()}"
    await context.update_character_name_tgt(character_id, f"{character_id}-tgt", origin)
    await context.update_character_pronouns(character_id, "they/them", origin)
    await context.update_character_notes(character_id, "notes", origin)


async def _detail_location_stub(context: ProjectContext, location_id: str, **_: object) -> None:
    """Lightweight location detailer stub."""
    origin = f"agent:test:{date.today().isoformat()}"
    await context.update_location_name_tgt(location_id, f"{location_id}-tgt", origin)
    await context.update_location_description(location_id, "desc", origin)


async def _detail_route_stub(context: ProjectContext, route_id: str, **_: object) -> None:
    """Lightweight route detailer stub."""
    origin = f"agent:test:{date.today().isoformat()}"
    await context.update_route_synopsis(route_id, f"synopsis-{route_id}", origin)
    await context.update_route_characters(route_id, ["mc"], origin)


async def _detail_glossary_stub(context: ProjectContext, **_: object) -> None:
    """Lightweight glossary stub."""
    origin = f"agent:test:{date.today().isoformat()}"
    await context.add_glossary_entry("term", "translation", "notes", origin)


def _approve_decisions(requests: list[str]) -> list[str]:
    """Decision handler stub.

    Returns:
        list[str]: Approve decisions for all requests.
    """
    _ = requests
    return ["approve"]


@pytest.mark.anyio
async def test_cli_context_resume_latest(monkeypatch: pytest.MonkeyPatch, tiny_vn_tmp: Path) -> None:
    """Invoke CLI context twice, resuming with latest thread-id from status snapshot."""
    project_path = tiny_vn_tmp

    # Patch out agents and HITL prompts
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_scene", _detail_scene_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_character", _detail_character_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_location", _detail_location_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_route", _detail_route_stub)
    monkeypatch.setattr("rentl_pipelines.flows.context_builder.detail_glossary", _detail_glossary_stub)
    monkeypatch.setattr("rentl_cli.commands.run._prompt_decisions", _approve_decisions)

    # First run: new thread id recorded in status
    result_first = await anyio.to_thread.run_sync(  # type: ignore[attr-defined]
        runner.invoke, app, ["context", "--project-path", str(project_path), "--verbosity", "debug"]
    )
    assert result_first.exit_code == 0, result_first.output
    status = load_phase_status(project_path)
    assert status is not None, "Expected context status snapshot"
    assert status.context is not None, "Expected context status snapshot"
    first_thread = status.context.thread_id
    assert first_thread.startswith("context"), "Expected context thread id prefix"

    # Second run: resume-latest should reuse the same thread id
    result_second = await anyio.to_thread.run_sync(  # type: ignore[attr-defined]
        runner.invoke,
        app,
        [
            "context",
            "--project-path",
            str(project_path),
            "--resume-latest",
            "--verbosity",
            "debug",
        ],
    )
    assert result_second.exit_code == 0, result_second.output
    status_after = load_phase_status(project_path)
    assert status_after is not None, "Expected context status after resume"
    assert status_after.context is not None, "Expected context status after resume"
    assert status_after.context.thread_id == first_thread, "Resume should reuse latest thread id"

    # Spot-check that metadata was written by stubs
    context = await load_project_context(project_path)
    for scene in context.scenes.values():
        assert scene.annotations.summary, "Scene summary should be present"
    for character in context.characters.values():
        assert character.name_tgt, "Character target name should be present"
