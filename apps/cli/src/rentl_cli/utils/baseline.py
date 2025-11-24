"""Baseline tiny_vn data generated from Pydantic models for repeatable resets."""
# ruff: noqa: RUF001

from __future__ import annotations

from pathlib import Path

import anyio
import orjson
from rentl_core.model.character import CharacterMetadata
from rentl_core.model.game import CharacterSet, GameMetadata, TimelineEntry, UIConstraints
from rentl_core.model.glossary import GlossaryEntry
from rentl_core.model.line import SourceLine, SourceLineMeta
from rentl_core.model.location import LocationMetadata
from rentl_core.model.route import RouteMetadata
from rentl_core.model.scene import SceneAnnotations, SceneMetadata


def _dump_jsonl(path: Path, entries: list[dict]) -> None:
    """Write a list of dicts as JSONL."""
    lines = [orjson.dumps(entry, option=orjson.OPT_APPEND_NEWLINE) for entry in entries]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(lines))


async def write_baseline(project_path: Path) -> None:
    """Write baseline tiny_vn metadata and scenes into project_path."""
    metadata_dir = project_path / "metadata"
    scenes_dir = project_path / "input" / "scenes"
    context_docs_dir = metadata_dir / "context_docs"
    for directory in (metadata_dir, scenes_dir, context_docs_dir):
        await anyio.Path(directory).mkdir(parents=True, exist_ok=True)

    game = GameMetadata(
        title="tiny_vn",
        title_origin="human",
        description="Small sample VN showcasing multi-route translation pipeline.",
        description_origin="human",
        source_lang="jpn",
        target_lang="eng",
        genres=["romance", "slice_of_life"],
        genres_origin="human",
        synopsis="A transfer student navigates friendships with Aya and Ren while preparing for the school festival.",
        synopsis_origin="human",
        timeline=[
            TimelineEntry(when="Day 1", event="Arrival at new school"),
            TimelineEntry(when="Day 2", event="Festival planning begins"),
            TimelineEntry(when="Day 3", event="Rooftop confession"),
        ],
        timeline_origin="human",
        ui=UIConstraints(max_line_length=42, allow_word_wrap=True, charset=CharacterSet.UNICODE),
    )
    async with await anyio.open_file(metadata_dir / "game.json", "w", encoding="utf-8") as stream:
        await stream.write(game.model_dump_json(indent=2))

    characters = [
        CharacterMetadata(
            id="mc",
            name_src="拓海",
            name_src_origin="human",
            name_tgt="Takumi",
            name_tgt_origin="human",
            pronouns="he/him",
            pronouns_origin="human",
            notes="Transfer student, thoughtful inner monologue.",
            notes_origin="human",
        ),
        CharacterMetadata(
            id="aya",
            name_src="綾",
            name_src_origin="human",
            name_tgt="Aya",
            name_tgt_origin="human",
            pronouns="she/her",
            pronouns_origin="human",
            notes="Cheerful classmate who loves practical jokes.",
            notes_origin="human",
        ),
        CharacterMetadata(
            id="ren",
            name_src="蓮",
            name_src_origin="human",
            name_tgt="Ren",
            name_tgt_origin="human",
            pronouns="she/her",
            pronouns_origin="human",
            notes="Stoic member of the festival committee.",
            notes_origin="human",
        ),
    ]
    _dump_jsonl(metadata_dir / "characters.jsonl", [c.model_dump(mode="json") for c in characters])

    locations = [
        LocationMetadata(
            id="classroom",
            name_src="教室",
            name_src_origin="human",
            name_tgt="Classroom",
            name_tgt_origin="human",
            description="Homeroom classroom with afternoon sun.",
            description_origin="human",
        ),
        LocationMetadata(
            id="school_rooftop",
            name_src="屋上",
            name_src_origin="human",
            name_tgt="Rooftop",
            name_tgt_origin="human",
            description="Windy rooftop overlooking the city.",
            description_origin="human",
        ),
    ]
    _dump_jsonl(metadata_dir / "locations.jsonl", [loc.model_dump(mode="json") for loc in locations])

    glossary = [
        GlossaryEntry(
            term_src="文化祭",
            term_src_origin="human",
            term_tgt="school festival",
            term_tgt_origin="human",
            notes="Use in narration unless characters use slang.",
            notes_origin="human",
        ),
        GlossaryEntry(
            term_src="先輩",
            term_src_origin="human",
            term_tgt="senpai",
            term_tgt_origin="human",
            notes="Keep in romaji.",
            notes_origin="human",
        ),
    ]
    _dump_jsonl(metadata_dir / "glossary.jsonl", [g.model_dump(mode="json") for g in glossary])

    routes = [
        RouteMetadata(
            id="common",
            name="Common Route",
            name_origin="human",
            scene_ids=["scene_c_00"],
            synopsis="Takumi meets Aya and Ren during the first week.",
            synopsis_origin="human",
            primary_characters=["mc", "aya", "ren"],
            primary_characters_origin="human",
        ),
        RouteMetadata(
            id="route_aya",
            name="Aya Route",
            name_origin="human",
            scene_ids=["scene_a_00"],
            synopsis="Takumi helps Aya prepare a surprise gallery.",
            synopsis_origin="human",
            primary_characters=["mc", "aya"],
            primary_characters_origin="human",
        ),
        RouteMetadata(
            id="route_ren",
            name="Ren Route",
            name_origin="human",
            scene_ids=["scene_r_00", "scene_r_01"],
            synopsis="Takumi supports Ren's festival strategy and late-night confession.",
            synopsis_origin="human",
            primary_characters=["mc", "ren"],
            primary_characters_origin="human",
        ),
    ]
    _dump_jsonl(metadata_dir / "routes.jsonl", [r.model_dump(mode="json") for r in routes])

    scenes = [
        SceneMetadata(
            id="scene_a_00",
            title="Late-Night Gallery",
            title_origin="human",
            route_ids=["route_aya"],
            annotations=SceneAnnotations(
                notes="Aya asks for help setting up her surprise gallery.",
                notes_origin="human",
                tags=["night", "gallery", "surprise", "collaboration"],
                tags_origin="human",
                summary="夜遅くに、Ayaが拓海（MC）を呼び寄せてサプライズギャラリーの設営を手伝うよう頼む。二人は展示方法を相談しながら協力することを決める。",
                summary_origin="human",
                primary_characters=["mc", "aya"],
                primary_characters_origin="human",
                locations=["classroom"],
                locations_origin="human",
            ),
            raw_file="scene_a_00.ks",
        ),
        SceneMetadata(
            id="scene_c_00",
            title="First Day Introductions",
            title_origin="human",
            route_ids=["common"],
            annotations=SceneAnnotations(
                notes="Takumi is welcomed to class.",
                notes_origin="human",
                tags=["intro", "choice", "firstday", "newstudent", "morning"],
                tags_origin="human",
                summary="朝のクラス紹介で、MCが自己紹介し、綾は明るく歓迎、蓮は冷静にアドバイス。誰と話すか選択する場面で期待と緊張が混ざった雰囲気になる。",
                summary_origin="human",
                primary_characters=["mc", "aya", "ren"],
                primary_characters_origin="human",
                locations=[],
                locations_origin="human",
            ),
            raw_file="scene_c_00.ks",
        ),
        SceneMetadata(
            id="scene_r_00",
            title="Festival Strategy",
            title_origin="human",
            route_ids=["route_ren"],
            annotations=SceneAnnotations(
                notes="Ren lays out the festival plan.",
                notes_origin="human",
                tags=["planning", "budget", "logistics", "collaboration", "time pressure"],
                tags_origin="human",
                summary="renが時間不足を訴え、mcとともに予算・搬入・人員配置の計画を整理しようとする。mcは図でまとめる提案をして、協力的な雰囲気で進める。",
                summary_origin="human",
                primary_characters=["mc", "ren"],
                primary_characters_origin="human",
                locations=["classroom"],
                locations_origin="human",
            ),
            raw_file="scene_r_00.ks",
        ),
        SceneMetadata(
            id="scene_r_01",
            title="Rooftop Confession",
            title_origin="human",
            route_ids=["route_ren"],
            annotations=SceneAnnotations(
                notes="Climactic confession after the festival.",
                notes_origin="human",
                tags=["rooftop", "confession", "night", "gratitude", "playful"],
                tags_origin="human",
                summary="夜風を感じながら屋上で二人は静かに話し合い、レンの手伝いへの感謝と笑顔の珍しさを共有した。最後にはレンが少しだけ見せるという照れ隠しで、和やかな雰囲気が残った。",
                summary_origin="human",
                primary_characters=["mc", "ren"],
                primary_characters_origin="human",
                locations=["school_rooftop"],
                locations_origin="human",
            ),
            raw_file="scene_r_01.ks",
        ),
    ]
    _dump_jsonl(metadata_dir / "scenes.jsonl", [s.model_dump(mode="json") for s in scenes])

    # Context docs (empty placeholder)
    await anyio.Path(context_docs_dir / "README.txt").write_text(
        "Add project-specific context docs here.\n", encoding="utf-8"
    )

    # Scene JSONL files
    scene_lines: dict[str, list[SourceLine]] = {
        "scene_c_00": [
            SourceLine(
                id="scene_c_00_0001",
                text="おはようございます、皆さん。今日から新しいクラスメイトが加わります。",
                meta=SourceLineMeta(
                    speaker="担任", speaker_origin="human", style_notes=["Formal greeting"], style_notes_origin="human"
                ),
            ),
            SourceLine(
                id="scene_c_00_0002",
                text="拓海です。よろしくお願いします。",
                meta=SourceLineMeta(speaker="mc", speaker_origin="human"),
            ),
            SourceLine(
                id="scene_c_00_0003",
                text="わー、ようこそ！私は綾。教室のことなら何でも聞いてね。",
                meta=SourceLineMeta(
                    speaker="aya",
                    speaker_origin="human",
                    style_notes=["Cheerful, informal"],
                    style_notes_origin="human",
                ),
            ),
            SourceLine(
                id="scene_c_00_0004",
                text="……蓮。質問があれば後で聞くといい。",
                meta=SourceLineMeta(
                    speaker="ren", speaker_origin="human", style_notes=["Stoic"], style_notes_origin="human"
                ),
            ),
            SourceLine(
                id="scene_c_00_0005",
                text="どっちと話してみようかな……？",
                meta=SourceLineMeta(
                    speaker="mc", speaker_origin="human", style_notes=["Internal monologue"], style_notes_origin="human"
                ),
            ),
            SourceLine(
                id="scene_c_00_0006",
                text="綾の笑顔に惹かれる",
                is_choice=True,
                meta=SourceLineMeta(
                    notes=["Branches to Aya route"],
                    notes_origin="human",
                    style_notes=["Choice label"],
                    style_notes_origin="human",
                ),
            ),
            SourceLine(
                id="scene_c_00_0007",
                text="蓮の真剣さに惹かれる",
                is_choice=True,
                meta=SourceLineMeta(
                    notes=["Branches to Ren route"],
                    notes_origin="human",
                    style_notes=["Choice label"],
                    style_notes_origin="human",
                ),
            ),
        ],
        "scene_a_00": [
            SourceLine(
                id="scene_a_00_0001",
                text="こんな遅くに呼び出してごめんね。手伝ってほしいことがあるの。",
                meta=SourceLineMeta(speaker="aya", speaker_origin="human"),
            ),
            SourceLine(
                id="scene_a_00_0002",
                text="何でも言って。僕にできることならやるよ。",
                meta=SourceLineMeta(speaker="mc", speaker_origin="human"),
            ),
            SourceLine(
                id="scene_a_00_0003",
                text="サプライズのギャラリーを作りたいんだ。一緒に展示方法を考えてくれる？",
                meta=SourceLineMeta(speaker="aya", speaker_origin="human"),
            ),
        ],
        "scene_r_00": [
            SourceLine(
                id="scene_r_00_0001",
                text="時間が足りない。予算も厳しい。どう進めればいい…",
                meta=SourceLineMeta(
                    speaker="ren", speaker_origin="human", style_notes=["Worried"], style_notes_origin="human"
                ),
            ),
            SourceLine(
                id="scene_r_00_0002",
                text="落ち着こう。タスクを整理して手伝うよ。",
                meta=SourceLineMeta(speaker="mc", speaker_origin="human"),
            ),
        ],
        "scene_r_01": [
            SourceLine(
                id="scene_r_01_0001",
                text="あの時、本当に助かった。…ありがとう。",
                meta=SourceLineMeta(
                    speaker="ren", speaker_origin="human", style_notes=["Soft tone"], style_notes_origin="human"
                ),
            ),
            SourceLine(
                id="scene_r_01_0002",
                text="少し笑った？珍しいね。",
                meta=SourceLineMeta(speaker="mc", speaker_origin="human"),
            ),
            SourceLine(
                id="scene_r_01_0003",
                text="……からかわないで。",
                meta=SourceLineMeta(speaker="ren", speaker_origin="human"),
            ),
        ],
    }

    for scene_id, lines in scene_lines.items():
        out_path = scenes_dir / f"{scene_id}.jsonl"
        _dump_jsonl(out_path, [line.model_dump(mode="json") for line in lines])
