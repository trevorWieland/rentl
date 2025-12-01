# rentl Data Schemas

This document defines the canonical data formats for rentl metadata, input scenes, and translation outputs. These schemas represent the **target design** including provenance tracking for human-in-the-loop (HITL) approval workflows.

---

## Table of Contents

1. [Schema Philosophy](#schema-philosophy)
2. [Provenance Tracking](#provenance-tracking)
3. [Metadata Schemas](#metadata-schemas)
   - [game.json](#gamejson)
   - [characters.jsonl](#charactersjsonl)
   - [glossary.jsonl](#glossaryjsonl)
   - [locations.jsonl](#locationsjsonl)
   - [routes.jsonl](#routesjsonl)
   - [scenes.jsonl](#scenesjsonl)
   - [style_guide.md](#style_guidemd)
   - [context_docs/](#context_docs)
4. [Input Schemas](#input-schemas)
   - [Scene Files (input/scenes/*.jsonl)](#scene-files)
5. [Output Schemas](#output-schemas)
   - [Translation Files (output/translations/*.jsonl)](#translation-files)
6. [File and ID Alignment](#file-and-id-alignment)

---

## Schema Philosophy

### Custom Fields and `extra="allow"`

All metadata models use Pydantic's `extra="allow"` configuration, which permits arbitrary custom fields beyond the schema-defined ones. This design serves two purposes:

1. **Human extensibility**: Users can add custom fields specific to their game engine or workflow (e.g., `text_color`, `camera_angle`, `voice_clip`).
2. **Agent behavior**: Agents can **read** custom fields to inform their decisions, but **cannot modify** them.

**Key principle**: Only schema-defined fields are agent-modifiable. Custom fields remain read-only for agents and can only be edited by humans directly in the files.

**Example**: A user adds `"is_bolded": true` to certain lines for their engine. Agents will see this field when reading scenes, but no tool will allow them to modify it. If you want agents to manage a field, add it to the schema definition in code.

---

## Provenance Tracking

### Purpose

Provenance tracking enables intelligent HITL approval by recording whether each field was last set by a human or an agent. This allows:

- Agents to freely fill in empty/missing fields
- Agents to refine their own prior work
- Protection of human-authored data via approval gates

### Format

For trackable fields, a corresponding `*_origin` field records the provenance:

- **`"human"`**: Field was set or last modified by a human
- **`"agent:<subagent_name>:<date>"`**: Field was set or last modified by the specified agent

**Example**: `"name_tgt_origin": "human"` or `"summary_origin": "agent:scene_detailer:2024-11-22"`

**Note**: We use `*_origin` rather than `*_source` to avoid confusion with source language fields (`*_src`).

### Which Fields Get Tracking

Provenance tracking applies to **content fields** where human vs. agent authorship affects HITL approval decisions.

**Fields that DO NOT get tracking**:
1. **Identifiers**: `id`, `scene_ids`, `route_ids` (immutable keys/references)
2. **Language config**: `source_lang`, `target_lang` (project structure)
3. **Immutable source text**: `SourceLine.text` (extracted, not authored in pipeline)
4. **File references & engine specifics**: `raw_file`, `ui.*`, `is_choice` (human-configured technical details)

**Fields that DO get tracking**: Everything else (names, descriptions, notes, summaries, lists, translations, etc.)

### Provenance Rules

- `*_origin` fields are **required** if the corresponding content field is non-null
- If a content field is null/empty, its `*_origin` should be omitted or null
- When an agent or human updates a tracked field, they **must** also update the `*_origin`

### HITL Approval Rules

Tools check provenance to determine if approval is needed:

**read_* tools**: Never require approval

**add_* tools**:
- `permissive` policy: Add without approval
- `strict` policy: Require approval

**update_* tools**:
- `permissive` policy: Update without approval (rare, for safe metadata)
- `standard` policy: Check field-level provenance
  - Empty/null field → update without approval
  - Agent-originated field → update without approval
  - Human-originated field → require approval
- `strict` policy: Always require approval

**delete_* tools**:
- `standard` policy: Check entry-level provenance
  - If **any** field has `human` origin → require approval
  - If all fields are agent/empty → allow deletion
- `strict` policy: Always require approval

---

## Metadata Schemas

### game.json

**Location**: `metadata/game.json`

**Description**: Top-level project metadata describing the game, languages, and UI constraints.

**Format**: Single JSON object

**Schema**:

```json
{
  "title": "Example VN",
  "title_origin": "human",
  "title_src": "例のビジュアルノベル",
  "title_src_origin": "human",
  "title_tgt": "Example VN",
  "title_tgt_origin": "human",
  "description": "Short description of the project",
  "description_origin": "human",
  "source_lang": "jpn",
  "target_lang": "eng",
  "genres": ["romance", "slice_of_life"],
  "genres_origin": "agent:game_analyzer:2024-11-22",
  "synopsis": "A transfer student navigates friendships while preparing for the school festival.",
  "synopsis_origin": "human",
  "timeline": [
    {"when": "2 years before", "event": "MC's father disappears"},
    {"when": "Day 1", "event": "MC arrives at new school"},
    {"when": "Day 3", "event": "School festival begins"}
  ],
  "timeline_origin": "human",
  "ui": {
    "max_line_length": 42,
    "allow_word_wrap": true,
    "charset": "unicode"
  }
}
```

**Field Definitions**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `title` | string | Yes | **Yes** | Primary project/game title (typically target language) |
| `title_src` | string | No | **Yes** | Game title in source language |
| `title_tgt` | string | No | **Yes** | Game title in target language (may differ from `title` for localization) |
| `description` | string | No | **Yes** | Short project description |
| `source_lang` | string | Yes | No | Source language code (ISO 639-3, e.g., "jpn") |
| `target_lang` | string | Yes | No | Target language code (ISO 639-3, e.g., "eng") |
| `genres` | string[] | No | **Yes** | Genre tags (free-form) |
| `synopsis` | string | No | **Yes** | Plot summary or premise |
| `timeline` | TimelineEntry[] | No | **Yes** | Chronological events (see below) |
| `ui` | UIConstraints | No | No | UI/formatting constraints (no tracking, engine-specific) |

**TimelineEntry Schema**:

```json
{"when": "Day 1", "event": "MC arrives at new school"}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `when` | string | Yes | Time reference (e.g., "Day 1", "2 years before game", "Chapter 3") |
| `event` | string | Yes | Brief event description |

**UIConstraints** (no provenance tracking - engine-specific):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `max_line_length` | integer | No | Maximum characters per line (null = no limit) |
| `allow_word_wrap` | boolean | No | Whether engine supports word wrapping (default: true) |
| `charset` | string | No | Character set restriction: `"ascii"`, `"unicode"`, `"shift_jis"`, `"euc_jp"` |

**Notes**:
- `timeline` provides chronological context for consistency checks (events may precede game start)
- Language codes should follow ISO 639-3 (three-letter codes)
- UI constraints are human-configured based on engine limitations

---

### characters.jsonl

**Location**: `metadata/characters.jsonl`

**Description**: Character roster with names, pronouns, and biographical notes.

**Format**: Newline-delimited JSON (one object per line)

**Schema** (per entry):

```jsonl
{"id": "aya", "name_src": "綾", "name_src_origin": "human", "name_tgt": "Aya", "name_tgt_origin": "human", "pronouns": "she/her", "pronouns_origin": "human", "notes": "Cheerful classmate who loves practical jokes.", "notes_origin": "human"}
{"id": "mc", "name_src": "拓海", "name_src_origin": "human", "name_tgt": "Takumi", "name_tgt_origin": "human", "pronouns": "he/him", "pronouns_origin": "human", "notes": "Transfer student, thoughtful inner monologue.", "notes_origin": "agent:character_detailer:2024-11-22"}
```

**Field Definitions**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `id` | string | Yes | No | Unique character identifier (slug/key) |
| `name_src` | string | Yes | **Yes** | Character name in source language |
| `name_tgt` | string | No | **Yes** | Localized name in target language |
| `pronouns` | string | No | **Yes** | Pronoun preferences (e.g., "she/her", "he/him", "they/them") |
| `notes` | string | No | **Yes** | Biographical notes, personality, speech patterns |

**Custom Fields**: Users may add engine-specific fields (e.g., `sprite_set`, `voice_actor`). Agents can read but not modify them.

---

### glossary.jsonl

**Location**: `metadata/glossary.jsonl`

**Description**: Canonical terminology, idioms, and translation guidance.

**Format**: Newline-delimited JSON

**Schema** (per entry):

```jsonl
{"term_src": "先輩", "term_src_origin": "human", "term_tgt": "senpai", "term_tgt_origin": "human", "notes": "Keep in romaji.", "notes_origin": "human"}
{"term_src": "文化祭", "term_src_origin": "human", "term_tgt": "school festival", "term_tgt_origin": "human", "notes": "Use in narration unless characters use slang.", "notes_origin": "human"}
```

**Field Definitions**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `term_src` | string | Yes | **Yes** | Term/phrase in source language |
| `term_tgt` | string | No | **Yes** | Preferred rendering in target language |
| `notes` | string | No | **Yes** | Translation guidance, context, usage notes |

**Usage**:
- `meta_glossary_curator` subagents may propose new entries or updates via HITL tools
- Translators reference this glossary for consistent terminology

---

### locations.jsonl

**Location**: `metadata/locations.jsonl`

**Description**: Recurring locations/settings with descriptions and mood cues.

**Format**: Newline-delimited JSON

**Schema** (per entry):

```jsonl
{"id": "classroom", "name_src": "教室", "name_src_origin": "human", "name_tgt": "Classroom", "name_tgt_origin": "human", "description": "Homeroom classroom with afternoon sun.", "description_origin": "agent:location_detailer:2024-11-22"}
{"id": "school_rooftop", "name_src": "屋上", "name_src_origin": "human", "name_tgt": "Rooftop", "name_tgt_origin": "human", "description": "Windy rooftop overlooking the city.", "description_origin": "human"}
```

**Field Definitions**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `id` | string | Yes | No | Unique location identifier |
| `name_src` | string | Yes | **Yes** | Location name in source language |
| `name_tgt` | string | No | **Yes** | Localized location name |
| `description` | string | No | **Yes** | Setting details, atmosphere, visual cues |

---

### routes.jsonl

**Location**: `metadata/routes.jsonl`

**Description**: Story routes/branches with scene ordering and character focus.

**Format**: Newline-delimited JSON

**Schema** (per entry):

```jsonl
{"id": "common", "name": "Common Route", "name_origin": "human", "scene_ids": ["scene_c_00"], "synopsis": "Takumi meets Aya and Ren during the first week.", "synopsis_origin": "human", "primary_characters": ["mc", "aya", "ren"], "primary_characters_origin": "human"}
{"id": "route_aya", "name": "Aya Route", "name_origin": "human", "scene_ids": ["scene_a_00"], "synopsis": "Takumi helps Aya prepare a surprise gallery.", "synopsis_origin": "agent:route_detailer:2024-11-22", "primary_characters": ["mc", "aya"], "primary_characters_origin": "agent:route_detailer:2024-11-22"}
```

**Field Definitions**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `id` | string | Yes | No | Unique route identifier |
| `name` | string | Yes | **Yes** | Human-readable route name |
| `scene_ids` | string[] | No | No | Ordered list of scene IDs in this route |
| `synopsis` | string | No | **Yes** | Route summary or description |
| `primary_characters` | string[] | No | **Yes** | Key character IDs associated with the route |

**Notes**:
- `scene_ids` defines the canonical order for route playthrough
- `scene_ids` is not provenance-tracked (structural list of references)

---

### scenes.jsonl

**Location**: `metadata/scenes.jsonl`

**Description**: Scene-level metadata including human notes and agent-generated annotations.

**Format**: Newline-delimited JSON

**Schema** (per entry):

```jsonl
{"id": "scene_c_00", "title": "First Day Introductions", "title_origin": "human", "route_ids": ["common"], "raw_file": "scene_c_00.ks", "annotations": {"notes": "Takumi is welcomed to class.", "notes_origin": "human", "tags": ["intro", "classroom"], "tags_origin": "human", "summary": "先生が新入生を紹介し、MCは自己紹介。綾は明るく歓迎し、蓮は冷静にアドバイス。MCは誰と話すか迷い、選択肢が提示される。", "summary_origin": "agent:scene_detailer:2024-11-22", "primary_characters": ["mc", "aya", "ren"], "primary_characters_origin": "agent:scene_detailer:2024-11-22", "locations": ["classroom"], "locations_origin": "agent:scene_detailer:2024-11-22"}}
```

**Field Definitions**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `id` | string | Yes | No | Unique scene identifier (matches scene file name in `input/scenes/`) |
| `title` | string | No | **Yes** | Human-readable scene title |
| `route_ids` | string[] | No | No | Route IDs that include this scene |
| `raw_file` | string | No | No | Original engine script file for reference |
| `annotations` | SceneAnnotations | No | N/A | Combined human/agent metadata (see below) |

**SceneAnnotations**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `notes` | string | No | **Yes** | Free-form notes (human or agent observations) |
| `tags` | string[] | No | **Yes** | Quick descriptive tags (e.g., "intro", "confession") |
| `summary` | string | No | **Yes** | Scene summary (typically in source language) |
| `primary_characters` | string[] | No | **Yes** | Character IDs appearing in the scene |
| `locations` | string[] | No | **Yes** | Location IDs where scene takes place |

**Notes**:
- Scene annotations blend human-authored context (notes, tags) with agent-generated analysis (summary, character/location detection)
- Summaries are typically written in the source language to avoid translation bias
- The `id` field must match the filename stem of the corresponding scene file (e.g., `scene_c_00` → `input/scenes/scene_c_00.jsonl`)

---

### style_guide.md

**Location**: `metadata/style_guide.md`

**Description**: Markdown-formatted style and localization guidelines.

**Format**: Free-form Markdown

**Purpose**:
- Define voice, tone, and point of view
- Specify honorific handling (keep, strip, explain)
- Provide typography and formatting rules
- Clarify localization vs. translation philosophy

**Example**:

```markdown
# Style Guide

## Keep honorifics without explanation
Terms like senpai, -kun, -san are all common knowledge for western audiences now. Keep them when localizing, and don't explain.

## Keep references as is
References to anime, tv shows, pop culture can remain as is, without finding a similar reference for the target language.

## Idioms should be translated subjectively
Don't translate idioms literally, be sure to find a similar expression in the target language.
```

**Notes**:
- No schema enforcement; agents read this as plain text context
- Should be written by humans and updated collaboratively
- Agents may reference style_guide.md when making translation decisions

---

### context_docs/

**Location**: `metadata/context_docs/`

**Description**: Directory for arbitrary supporting documents (prequels, game manuals, wikis, developer notes, etc.).

**Formats**: Markdown (`.md`), plain text (`.txt`), PDF (`.pdf`)

**Purpose**:
- Provide additional context for agents (e.g., lore, character backstories, world-building)
- Reference materials that inform translation decisions

**Example Files**:
- `diary_excerpt.md` – Character diary entries for backstory
- `product_page.md` – Official game description/synopsis
- `walkthrough.txt` – Gameplay walkthrough with plot details

**Usage**:
- Agents can list and read these documents via tools (`list_context_docs`, `read_context_doc`)
- No schema validation; treat as read-only reference material
- Humans can add/update these files freely

---

## Input Schemas

### Scene Files

**Location**: `input/scenes/*.jsonl`

**Description**: Source-language scene scripts, one file per scene, with one JSON object per line.

**Format**: Newline-delimited JSON

**Naming Convention**: File name stem matches scene ID (e.g., `scene_c_00.jsonl` for scene `scene_c_00`)

**Schema** (per line):

```jsonl
{"id": "scene_c_00_0001", "text": "おはようございます、皆さん。今日から新しいクラスメイトが加わります。", "is_choice": false, "meta": {"speaker": "担任", "speaker_origin": "human", "notes": [], "notes_origin": null, "style_notes": ["Formal greeting"], "style_notes_origin": "human", "idioms": [], "idioms_origin": null, "references": [], "references_origin": null}}
{"id": "scene_c_00_0002", "text": "拓海です。よろしくお願いします。", "is_choice": false, "meta": {"speaker": "mc", "speaker_origin": "human", "notes": [], "notes_origin": null, "style_notes": [], "style_notes_origin": null, "idioms": [], "idioms_origin": null, "references": [], "references_origin": null}}
{"id": "scene_c_00_0006", "text": "綾の笑顔に惹かれる", "is_choice": true, "meta": {"speaker": null, "speaker_origin": null, "notes": ["Branches to Aya route"], "notes_origin": "human", "style_notes": ["Choice label"], "style_notes_origin": "human", "idioms": [], "idioms_origin": null, "references": [], "references_origin": null}}
```

**Field Definitions**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `id` | string | Yes | No | Stable line identifier (e.g., `scene_c_00_0001`) |
| `text` | string | Yes | No | Source-language text of the line (immutable) |
| `is_choice` | boolean | No | No | Whether this line is a player choice option (default: false) |
| `meta` | SourceLineMeta | No | N/A | Line-level metadata (see below) |

**SourceLineMeta**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `speaker` | string or null | No | **Yes** | Speaker identifier or special values (see below) |
| `notes` | string[] | No | **Yes** | General metadata (e.g., "Branches to Aya route", "Voice clip cut here") |
| `style_notes` | string[] | No | **Yes** | Translation style hints (e.g., "Stoic", "Internal monologue", "Cheerful") |
| `idioms` | string[] | No | **Yes** | Idioms detected or noted in the line |
| `references` | string[] | No | **Yes** | Cultural/media references |

**Speaker Values**:
- **Character ID** (e.g., `"aya"`): Line spoken by that character
- **`null`**: No speaker information or non-dialogue line
- **`"narration"`**: Explicit narration
- **`"???"`**: Unknown or masked speaker (mystery/surprise reveal)

**Notes on Meta Fields**:
- **`speaker`**: May come from extraction as `???` and be revealed/corrected later by agents or humans
- **`notes`**: General metadata not specific to translation style (route branches, technical notes, etc.)
- **`style_notes`**: Guidance specifically for translators (tone, register, speech patterns)
- **`idioms` / `references`**: Typically populated by detection agents during pipeline runs

**Custom Fields**:
- Users may add custom fields to `meta` (e.g., `"voice_clip": "v00023"`, `"text_color": "#FF99CC"`)
- Agents can **read** custom fields but **cannot modify** them
- If you want agents to manage a field, add it to the schema in code

**Notes**:
- Line IDs must be stable across versions (used to align source/translation)
- Scene-level metadata (route, synopsis, etc.) belongs in `scenes.jsonl`, not here

---

## Output Schemas

### Translation Files

**Location**: `output/translations/*.jsonl`

**Description**: Aligned source-target line pairs with QA metadata.

**Format**: Newline-delimited JSON

**Naming Convention**: Matches input scene file name stem (e.g., `scene_c_00.jsonl` for translations of `input/scenes/scene_c_00.jsonl`)

**Schema** (per line):

```jsonl
{"id": "scene_c_00_0001", "text_src": "おはようございます、皆さん。今日から新しいクラスメイトが加わります。", "text_tgt": "Good morning, everyone. Starting today, we have a new classmate joining us.", "text_tgt_origin": "agent:scene_translator:2024-11-22", "meta": {"checks": {"pronoun_consistency": [true, ""], "style_guide_compliance": [true, ""]}}}
{"id": "scene_c_00_0002", "text_src": "拓海です。よろしくお願いします。", "text_tgt": "I'm Takumi. Nice to meet you.", "text_tgt_origin": "agent:scene_translator:2024-11-22", "meta": {"checks": {"pronoun_consistency": [true, ""], "honorific_check": [true, "Used 'Nice to meet you' per style guide"]}}}
```

**Field Definitions**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `id` | string | Yes | No | Line identifier (matches source line ID from `input/scenes/*.jsonl`) |
| `text_src` | string | Yes | No | Original source text (copied from input, immutable) |
| `text_tgt` | string | Yes | **Yes** | Translated target-language text |
| `meta` | TranslationMeta | No | N/A | Translation and QA metadata (see below) |

**TranslationMeta**:

| Field | Type | Required | Provenance Tracked | Description |
|-------|------|----------|-------------------|-------------|
| `checks` | object | No | No | QA check results (always agent-generated, see format below) |

**Checks Format**:

Each check is a key-value pair where:
- **Key**: Check name (e.g., `"pronoun_consistency"`, `"style_guide_compliance"`, `"line_length"`)
- **Value**: `[pass: boolean, note: string]` tuple
  - `pass`: `true` if check passed, `false` if failed
  - `note`: Optional explanation or context

**Example Checks**:

```json
{
  "checks": {
    "pronoun_consistency": [true, ""],
    "style_guide_compliance": [true, ""],
    "line_length": [false, "Line exceeds 42 characters (actual: 58)"],
    "honorific_check": [true, "Kept 'senpai' per style guide"]
  }
}
```

**Custom Fields**:
- Users may add custom fields to `meta` for engine-specific data
- Agents can read but not modify custom fields
- Example: `"voice_clip": "v00023"` preserved from source line

**Version Management**:
- Git is the primary version control mechanism
- Users should commit translations regularly
- No internal revision system in rentl (all versioning via git history)

**Notes**:
- Translation files are typically generated by `scene_translator` and refined by `scene_editor` subagents
- QA checks accumulate as different subagents run (style checker, consistency checker, formatting checker)
- Failed checks may trigger retranslation or flag lines for human review

---

## File and ID Alignment

### Scene to Translation Mapping

Input scene files and output translation files are aligned by **filename** and **line ID**:

**Filename Alignment**:
- Input: `input/scenes/scene_c_00.jsonl`
- Output: `output/translations/scene_c_00.jsonl`
- The filename stem (`scene_c_00`) must match exactly

**Line ID Alignment**:
- Each line in the input scene has a unique `id` (e.g., `"scene_c_00_0001"`)
- The corresponding translated line in the output file uses the **same `id`**
- This allows source and target to be paired/aligned for review and analysis

**Example**:

**input/scenes/scene_c_00.jsonl**:
```jsonl
{"id": "scene_c_00_0001", "text": "おはよう。", "is_choice": false, "meta": {...}}
{"id": "scene_c_00_0002", "text": "行こう。", "is_choice": false, "meta": {...}}
```

**output/translations/scene_c_00.jsonl**:
```jsonl
{"id": "scene_c_00_0001", "text_src": "おはよう。", "text_tgt": "Morning.", "text_tgt_origin": "agent:scene_translator:2024-11-22", "meta": {...}}
{"id": "scene_c_00_0002", "text_src": "行こう。", "text_tgt": "Let's go.", "text_tgt_origin": "agent:scene_translator:2024-11-22", "meta": {...}}
```

**Important**:
- The `id` field is the **primary key** for alignment
- Line IDs must be stable across versions and edits
- Filenames must match between `input/scenes/` and `output/translations/`
- This alignment enables tools to easily match source and target for QA, review, and export

---

## Summary

This schema design balances:

- **Human control**: Provenance tracking (`*_origin`) protects human-authored data
- **Agent autonomy**: Agents can fill gaps and refine their own work without interruptions
- **Extensibility**: Custom fields support diverse game engines and workflows
- **Simplicity**: Provenance format is human-readable in git diffs
- **Clarity**: `*_origin` (provenance) is distinct from `*_src` (source language)

All schemas use Pydantic models in code with `extra="allow"` to preserve custom fields. Only schema-defined fields are agent-modifiable; custom fields remain read-only for agents.
