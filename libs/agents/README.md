# rentl-agents: Tools and Subagent Implementation Guide

This document provides implementation guidance for building tools and subagents for rentl's translation pipeline.

---

## Overview

The `rentl-agents` package contains:

- **Subagents**: Specialized agents for context building, translation, and editing (style/consistency/review)
- **Tools**: LangChain tools with HITL approval gating and provenance checks
- **LLM backends**: Wrappers for OpenAI-compatible endpoints
- **Graph helpers**: Convenience exports/typing glue

**File structure**:
```
libs/agents/src/rentl_agents/
  backends/
    base.py           # LLM backend abstractions
    openai_like.py    # ChatOpenAI wrapper
  graph/
    engine.py         # Shared exports for subagents (legacy naming)
  subagents/
    *.py              # Individual subagent implementations (context, translation, QA)
  tools/
    scene.py          # Scene-related tool implementations
    character.py      # Character tool implementations
    glossary.py       # Glossary tool implementations
    route.py          # Route tool implementations
  translation.py    # Translation tool implementations (MTL + write_translation)
  qa.py             # QA tool implementations (style/consistency/review)
```

---

## Standardized tool naming and subagent catalog

Use `{DATA}_{CRUD}_{THING}` for tool names (data domain, operation, specificity). The lists below are the canonical tool
and subagent map.

### Tool catalog
- Scenes: `scene_read_metadata`, `scene_read_overview`, `scene_read_redacted`, `scene_update_summary`,
  `scene_update_tags`, `scene_update_primary_characters`, `scene_update_locations`
- Characters: `character_read_entry`, `character_create_entry`, `character_update_name_tgt`,
  `character_update_pronouns`, `character_update_notes`, `character_delete_entry`
- Locations: `location_read_entry`, `location_create_entry`, `location_update_name_tgt`,
  `location_update_description`, `location_delete_entry`
- Routes: `route_read_entry`, `route_create_entry`, `route_update_synopsis`, `route_update_primary_characters`,
  `route_delete_entry`
- Glossary: `glossary_search_term`, `glossary_read_entry`, `glossary_create_entry`, `glossary_update_entry`,
  `glossary_merge_entries`, `glossary_delete_entry`
- Style/UI: `styleguide_read_full`, `ui_read_settings`
- Translation: `translation_check_mtl_available`, `translation_create_mtl_suggestion`, `translation_create_line`,
  `translation_update_line`, `translation_read_scene`
- QA records: `translation_create_style_check`, `translation_create_consistency_check`,
  `translation_create_review_check`
- Context docs: `contextdoc_list_all`, `contextdoc_read_doc`
- Status: `context_read_status`

### Subagent catalog (single-purpose)

**Context phase**
- `scene_summary_detailer`: Write the summary for one scene. Tools: scene_read_overview, scene_read_metadata,
  scene_read_redacted, character_read_entry, location_read_entry, glossary_search_term/read_entry,
  contextdoc_list_all/read_doc, scene_update_summary.
- `scene_tag_detailer`: Assign tags for one scene. Tools: scene_read_overview, scene_read_metadata,
  character_read_entry, location_read_entry, glossary_search_term/read_entry, contextdoc_list_all/read_doc,
  scene_update_tags.
- `scene_primary_character_detailer`: Set primary characters for one scene (and stub missing ones). Tools:
  scene_read_overview, scene_read_metadata, character_read_entry, character_create_entry,
  glossary_search_term/read_entry, contextdoc_list_all/read_doc, scene_update_primary_characters.
- `scene_location_detailer`: Set location IDs for one scene and enrich those locations. Tools: scene_read_overview,
  scene_read_metadata, location_read_entry, location_create_entry, location_update_name_tgt,
  location_update_description, glossary_search_term/read_entry, contextdoc_list_all/read_doc, scene_update_locations.
- `scene_glossary_detailer`: Add or update glossary terms discovered in a scene. Tools: scene_read_overview,
  glossary_search_term, glossary_read_entry, glossary_create_entry, glossary_update_entry,
  contextdoc_list_all/read_doc.
- `route_outline_builder`: Write synopsis and primary cast for one route. Tools: route_read_entry,
  scene_read_overview (for route scenes), character_read_entry, contextdoc_list_all/read_doc,
  route_update_synopsis, route_update_primary_characters.
- `meta_character_curator`: Polish/merge/delete characters globally. Tools: character_read_entry,
  character_update_name_tgt, character_update_pronouns, character_update_notes, character_create_entry,
  character_delete_entry, glossary_search_term/read_entry, contextdoc_list_all/read_doc.
- `meta_location_curator`: Polish/merge/delete locations globally. Tools: location_read_entry,
  location_update_name_tgt, location_update_description, location_create_entry, location_delete_entry,
  contextdoc_list_all/read_doc.
- `meta_glossary_curator`: Deduplicate/prune/polish glossary entries. Tools: glossary_search_term,
  glossary_read_entry, glossary_create_entry, glossary_update_entry, glossary_merge_entries,
  glossary_delete_entry, contextdoc_list_all/read_doc.

**Translation phase**
- `scene_translator`: Translate one scene end-to-end (direct). Tools: scene_read_overview, styleguide_read_full,
  ui_read_settings, glossary_read_entry/search_term, character_read_entry, location_read_entry,
  translation_create_line (or translation_update_line when overwrite is allowed).

**Editing phase**
- `scene_style_checker`: Style/UI compliance for one scene. Tools: translation_read_scene, styleguide_read_full,
  ui_read_settings, translation_create_style_check.
- `scene_translation_reviewer`: Fidelity/fluency review for one scene. Tools: translation_read_scene,
  scene_read_overview, styleguide_read_full, translation_create_review_check.
- `consistency_checker`: Per-scene consistency pass. Tools: translation_read_scene,
  translation_create_consistency_check.

These names supersede older examples in this file; keep them stable so HITL `interrupt_on` wiring remains predictable.

---

## Tool design (shared implementations + subagent selection)

- Tool modules now expose **context-accepting functions only** (e.g., `read_scene(context, scene_id)`,
  `update_route_synopsis(context, ...)`). They no longer export `build_*` functions.
- Each subagent file owns its own `_build_tools(...)` that:
  - wraps only the needed shared functions in `@tool` wrappers,
  - holds per-run state (e.g., single-use guards) local to the subagent,
  - defines the exact toolbox that subagent is allowed to use.
- HITL/provenance checks remain inside the shared implementations; interrupts still key off tool names (keep names
  stable).

**Naming convention**

- `scene_*` subagents operate on a single scene (e.g., `scene_summary_detailer`, `scene_tag_detailer`,
  `scene_style_checker`, `scene_translation_reviewer`).
- `route_*` subagents span related scenes (e.g., `route_consistency_checker`).
- `curate_*` subagents are game-level polish/dedupe (e.g., `curate_glossary`, `curate_characters`, `curate_locations`).
- Subagent toolboxes may include shared tools outside their primary entity when justified (e.g., a scene detailer may
  call `add_glossary_entry` but not `delete_glossary_entry`).

**Why this structure**

- Single source of truth for tool behavior, provenance, and HITL checks.
- Clear visibility into which subagent can call which tools (tool selection lives beside the subagent).
- Avoids duplication of tool logic across subagents while keeping fine-grained permissions.

---

## Subagent Architecture

<Warning>
**Critical distinction:** rentl uses **LangChain agents** for subagents, orchestrated by deterministic pipelines. There
are no LLM “coordinator” agents at the top level.
</Warning>

### Creating Subagents

Subagents are created with `create_agent`; pipelines invoke the returned runnable graph directly. Each file owns a single
subagent. Example: a single-purpose scene summary detailer.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import BaseTool, tool
from langgraph.graph.state import CompiledStateGraph
from rentl_core.context.project import ProjectContext
from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.tools.scene import scene_read_overview, scene_update_summary
from rentl_agents.tools.character import character_read_entry
from rentl_agents.tools.location import location_read_entry
from rentl_agents.tools.glossary import glossary_read_entry, glossary_search_term
from rentl_agents.tools.context_docs import contextdoc_list_all, contextdoc_read_doc


SYSTEM_PROMPT = """You are a scene summary specialist. Produce a concise summary in the source language using the
provided tools. Do not write tags or other metadata."""


def create_scene_summary_detailer_subagent(context: ProjectContext, *, allow_overwrite: bool, checkpointer) -> CompiledStateGraph:
    tools = _build_scene_summary_tools(context, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"scene_update_summary": True})],
        checkpointer=checkpointer,
    )


def _build_scene_summary_tools(context: ProjectContext, *, allow_overwrite: bool) -> list[BaseTool]:
    """Local tool selection capturing the shared ProjectContext."""
    written: set[str] = set()

    @tool("scene_read_overview")
    async def read_overview(scene_id: str) -> str:
        return await scene_read_overview(context, scene_id)

    @tool("scene_update_summary")
    async def update_summary(scene_id: str, summary: str) -> str:
        return await scene_update_summary(context, scene_id, summary, written_summary=written)

    @tool("character_read_entry")
    def read_character(character_id: str) -> str:
        return character_read_entry(context, character_id)

    @tool("location_read_entry")
    def read_location(location_id: str) -> str:
        return location_read_entry(context, location_id)

    @tool("glossary_search_term")
    async def search_glossary(query: str) -> str:
        return await glossary_search_term(context, query)

    @tool("glossary_read_entry")
    async def read_glossary(term_src: str) -> str:
        return await glossary_read_entry(context, term_src)

    @tool("contextdoc_list_all")
    async def list_docs() -> str:
        return await contextdoc_list_all(context)

    @tool("contextdoc_read_doc")
    async def read_doc(filename: str) -> str:
        return await contextdoc_read_doc(context, filename)

    return [
        read_overview,
        update_summary,
        read_character,
        read_location,
        search_glossary,
        read_glossary,
        list_docs,
        read_doc,
    ]
```

### Subagent characteristics

- Single-purpose scope with a clear definition of done (e.g., write only the scene summary).
- Created with `create_agent`; tools are injected via local `@tool` wrappers that capture the shared
  `ProjectContext`.
- Optional middleware: `HumanInTheLoopMiddleware` for approvals and `TodoListMiddleware` for self-planning.
- No direct filesystem access or direct `ProjectContext` writes; all mutations go through tools.

### Middleware for Subagents

**Default:** No middleware (only specialized tools)

**Optional:** TodoListMiddleware for complex multi-step tasks

```python
from langchain.agents.middleware import TodoListMiddleware

graph = create_agent(
    model=model,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
    middleware=[TodoListMiddleware()]  # Optional: task planning
)
```

**Never use:** FilesystemMiddleware (conflicts with specialized tools)

---

## Subagent Tool-Only Access

**Critical rule:** Subagents interact with metadata ONLY via tools—never through direct file operations or context
document reads.

**Why:**
1. **Provenance enforcement**: All writes must go through tools that track `*_origin` fields
2. **HITL gating**: Tools handle approval workflows for human-authored data
3. **Conflict detection**: Tools implement locking and concurrent update detection
4. **Immediate visibility**: Tool updates reflect instantly for all concurrent agents

**Forbidden operations for subagents:**
- ❌ Direct file reads (`open()`, `Path.read_text()`, etc.)
- ❌ Filesystem middleware (`ls`, `read_file`, `write_file`)
- ❌ Bypassing tools to modify `ProjectContext` directly

**Required pattern:**
```python
# ✅ Good: Use tools
@tool
async def read_character(char_id: str, runtime: ToolRuntime) -> str:
    context = runtime.context.project_context
    char = context.get_character(char_id)  # Via context
    return format_character_data(char)

# ❌ Bad: Direct file access
async def read_character_file(char_id: str) -> str:
    with open(f"metadata/characters/{char_id}.json") as f:
        return f.read()  # Bypasses provenance, locking, conflict detection!
```

### Complete CRUD Tool Coverage

Each entity type needs comprehensive tool coverage:

**Scenes:**
- `read_scene(scene_id)` - Get scene metadata + transcript
- `update_scene_summary(scene_id, summary)` - Modify summary
- `update_scene_tags(scene_id, tags)` - Modify tags
- `update_scene_characters(scene_id, character_ids)` - Modify character list
- `update_scene_locations(scene_id, location_ids)` - Modify location list

**Characters:**
- `read_character(char_id)` - Get character metadata
- `update_character_name(char_id, name_tgt)` - Modify target name
- `update_character_pronouns(char_id, pronouns)` - Modify pronouns
- `update_character_bio(char_id, bio)` - Modify bio/notes
- `add_character(char_id, ...)` - Create new character

**Glossary:**
- `search_glossary(term)` - Find matching entries
- `read_glossary_entry(term_src)` - Get specific entry
- `add_glossary_entry(term_src, term_tgt, notes)` - Create entry
- `update_glossary_entry(term_src, term_tgt, notes)` - Modify entry
- `delete_glossary_entry(term_src)` - Remove entry

**Context Docs (read-only):**
- `list_context_docs()` - List available documents
- `read_context_doc(filename)` - Get document contents

### Context Injection

Tools capture the shared `ProjectContext` via closures inside each `_build_*_tools` helper. No middleware is required
for context injection; middleware is reserved for HITL and planning behaviors.

**Key points:**
- Context is passed to the subagent factory and captured when building tools
- All concurrent subagents share the same `ProjectContext` instance
- Updates are immediately visible to all agents

---

## Tool Categories and Approval Policies

Tools are categorized by their operation type. Each category has default approval policies based on risk and provenance
tracking.

### read_* Tools

**Purpose**: Retrieve data without modification

**Approval policy**: Always `permissive` (never require human approval)

**Examples**:
- `scene_read_overview`: Get scene metadata + transcript
- `character_read_entry`: Get character bio/pronouns
- `glossary_read_entry` or `glossary_search_term`: Read or search glossary entries
- `contextdoc_list_all`: List available context documents

**Implementation**:

```python
from langchain_core.tools import tool
from rentl_agents.tools.character import character_read_entry

def _build_tools(context: ProjectContext) -> list[BaseTool]:
    @tool("character_read_entry")
    def read_character(character_id: str) -> str:
        """Return character metadata."""
        return character_read_entry(context, character_id)

    return [read_character]
```

**Guidelines**:
- Return formatted strings (easier for LLMs to parse than JSON)
- Include all relevant context in the response
- No side effects—read-only operations

---

### add_* Tools

**Purpose**: Create new entries in JSONL files

**Approval policy**:
- `permissive`: For low-risk additions (glossary entries, tags)
- `strict`: For structural changes (new characters, new routes)

**Examples**:
- `glossary_create_entry`: Propose new glossary term (permissive)
- `character_create_entry`: Create new character entry (strict)
- `route_create_entry`: Create new route (strict)

**Implementation**:

```python
from rentl_agents.tools.glossary import glossary_create_entry

def _build_glossary_tools(context: ProjectContext) -> list[BaseTool]:
    @tool("glossary_create_entry")
    async def create_glossary(term_src: str, term_tgt: str, notes: str | None = None) -> str:
        """Add a glossary entry with provenance tracking."""
        return await glossary_create_entry(context, term_src, term_tgt, notes=notes)

    return [create_glossary]
```

**Guidelines**:
- Always set `*_origin` fields when creating new entries
- Use agent name + date in origin string: `f"agent:{subagent_name}:{date.today()}"`
- Validate input before creating (check for duplicates, required fields)

---

### update_* Tools

**Purpose**: Modify existing fields in metadata

**Approval policy**: `standard` (check `*_origin` provenance)

**Provenance logic**:
1. If field is empty/null → update without approval
2. If `field_origin == "agent:*"` → update without approval (agent refining its own work)
3. If `field_origin == "human"` → **require approval** (protecting human data)

**Examples**:
- `character_update_notes`: Update character notes
- `scene_update_summary`: Revise scene summary
- `glossary_update_entry`: Improve glossary guidance

**Implementation**:

```python
from rentl_agents.tools.character import character_update_notes

def _build_character_tools(context: ProjectContext) -> list[BaseTool]:
    @tool("character_update_notes")
    async def update_notes(character_id: str, notes: str) -> str:
        """Update character notes with provenance/HITL checks."""
        return await character_update_notes(context, character_id, notes, updated_notes=set())

    return [update_notes]
```

**Guidelines**:
- Check provenance before updating: `if field_origin == "human": # pause for approval`
- Always update the corresponding `*_origin` field after modification
- Provide clear error messages for invalid inputs
- LangChain `HumanInTheLoopMiddleware` handles the actual approval pause

#### Conflict Detection in update_* Tools

When multiple subagents run concurrently, they might try to update the same field. `ProjectContext` implements
**feedback-providing locks** to handle this intelligently:

```python
@tool
async def update_character_bio(
    char_id: str,
    new_bio: str,
    runtime: ToolRuntime
) -> str:
    """Update character bio with conflict detection."""
    context = runtime.context.project_context

    # ProjectContext.update_character_bio handles:
    # 1. Entity-level locking (waits if another agent is updating this character)
    # 2. Conflict detection (checks if field was recently updated)
    # 3. Feedback (returns message if concurrent update detected)
    # 4. Persistence (writes to disk immediately)

    result = await context.update_character_bio(
        char_id,
        new_bio,
        origin="agent:character_detailer"
    )

    return result  # Either success message or conflict notification
```

**How conflict detection works:**
1. **Subagent 1** updates bio → acquires lock, updates, writes file, releases lock
2. **Subagent 2** (concurrent) → waits for lock, then acquires it
3. **Subagent 2** sees bio was updated 2 seconds ago
4. **Tool returns feedback**:
   ```
   CONCURRENT UPDATE DETECTED
   Bio was updated 2.0s ago.
   Current: Cheerful high school student
   Your proposed: Main protagonist and student council member

   Review and retry if your update is still needed.
   ```
5. **Subagent 2 decides**: Skip (redundant), combine both, or retry

**Benefits:**
- ✅ No data loss (second update doesn't blindly overwrite first)
- ✅ Intelligent coordination (agents see each other's work)
- ✅ Agents make decisions (human-like collaboration)
- ✅ No deadlocks (locks are held only during actual update)

**Implementation in ProjectContext:**
```python
class ProjectContext:
    async def update_character_bio(
        self,
        char_id: str,
        new_bio: str,
        origin: str,
        conflict_threshold_seconds: float = 30
    ) -> str:
        # Entity-level lock
        async with self._character_locks[char_id]:
            char = self.characters[char_id]
            current_bio = char.bio

            # Track recent updates
            update_key = ("character", char_id, "bio")
            last_update = self._recent_updates.get(update_key, 0)
            time_since_update = time.time() - last_update

            # Detect concurrent update
            if time_since_update < conflict_threshold_seconds and current_bio:
                return f"CONCURRENT UPDATE DETECTED\n..."

            # No conflict - proceed
            char.bio = new_bio
            char.bio_origin = origin
            self._recent_updates[update_key] = time.time()

            # Write immediately
            await write_character_metadata(self.project_path, char)

            return f"Successfully updated bio for {char_id}"
```

---

### delete_* Tools

**Purpose**: Remove entries from JSONL files.

**Approval policy**:
- `standard`: Require approval when any tracked field is human-authored.
- `strict`: Always require approval.

**Examples**:
- `glossary_delete_entry`: Remove a glossary term.
- `character_delete_entry`: Remove a character (after provenance check).

**Implementation**:

```python
from rentl_agents.tools.glossary import glossary_delete_entry

def _build_glossary_delete_tool(context: ProjectContext) -> list[BaseTool]:
    @tool("glossary_delete_entry")
    async def delete_glossary(term_src: str) -> str:
        """Delete a glossary entry, honoring HITL for human-authored fields."""
        return await glossary_delete_entry(context, term_src)

    return [delete_glossary]
```

---

## Provenance Tracking Best Practices

- Always set `*_origin` when creating or updating fields using the format `agent:<subagent_name>:YYYY-MM-DD`.
- Preserve human-authored data: tools should return approval requests when `*_origin == "human"`.
- Update origin alongside the field:

```python
origin = f"agent:scene_summary_detailer:{date.today()}"
scene.annotations.summary = new_summary
scene.annotations.summary_origin = origin
```

---

## HITL Integration (LangChain)

Use `HumanInTheLoopMiddleware` with `interrupt_on` matching the write tools that should pause when provenance requires
approval. Prefer the shared helper `run_with_human_loop` so CLI/TUI frontends can resume via thread IDs.

```python
await run_with_human_loop(
    scene_agent,
    {"messages": [{"role": "user", "content": user_prompt}]},
    decision_handler=my_decision_fn,
    thread_id="context:scene_a_00",
)
```

---

## Tool Access Control

Use the catalog above as the source of truth for tool selection. Context subagents get only the tools they need for a
single task (summary, tags, characters, locations, glossary); translation subagents stay read-heavy plus translation
write tools; editing subagents read translations/context and record QA checks. Keep toolboxes minimal to avoid scope
creep.
