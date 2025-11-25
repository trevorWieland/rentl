# rentl-agents: Tools and Subagent Implementation Guide

This document provides implementation guidance for building tools and subagents for rentl's translation pipeline.

---

## Overview

The `rentl-agents` package contains:

- **Subagents**: Specialized agents for context building, translation, and editing
- **Tools**: LangChain tools with HITL approval gating
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
    *.py              # Individual subagent implementations
  tools/
    scene.py          # Scene-related tools
    metadata.py       # Character/glossary/route tools
```

---

## Subagent Architecture

<Warning>
**Critical distinction:** rentl uses **LangChain agents** for subagents, orchestrated by deterministic pipelines. There are no LLM “coordinator” agents at the top level.
</Warning>

### Creating Subagents

Subagents are created using `create_agent` from `langchain.agents`; pipelines call the returned runnable graph directly:

```python
from langchain.agents import create_agent

# Step 1: Build LangChain agent graph
scene_detailer_graph = create_agent(
    model=model,
    tools=build_scene_tools(context, scene_id),
    system_prompt=SYSTEM_PROMPT
    # No middleware parameter = no default tools
)

scene_detailer = scene_detailer_graph  # Pipelines invoke this runnable with shared context
```

### Subagent Implementation Pattern

Each subagent file should follow this pattern:

```python
"""Scene detailer subagent.

This subagent enriches scene metadata with summaries, tags, characters, and locations.
"""

from langchain.agents import create_agent
from pydantic import BaseModel, Field
from rentl_core.context.project import ProjectContext
from rentl_core.util.logging import get_logger

from rentl_agents.backends.base import get_default_chat_model
from rentl_agents.tools.scene import build_scene_tools


class SceneDetailResult(BaseModel):
    """Result structure from scene detailer subagent."""
    scene_id: str = Field(description="Scene identifier that was detailed.")
    summary: str | None = Field(description="Scene summary.")
    tags: list[str] = Field(description="Scene tags.")
    primary_characters: list[str] = Field(description="Primary character IDs.")
    locations: list[str] = Field(description="Location IDs.")


logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a scene analysis assistant.

Your task is to enrich scene metadata by:
1. Reading the scene transcript
2. Writing a concise summary (2-3 sentences)
3. Identifying tags that describe the scene
4. Identifying primary characters (who speak or are mentioned)
5. Identifying locations where the scene takes place

Use the provided tools to read scene data and update metadata."""


def create_scene_detailer_subagent(
    context: ProjectContext,
    scene_id: str,
    *,
    allow_overwrite: bool = False
):
    """Create scene detailer subagent for a specific scene and return the runnable graph."""
    tools = build_scene_tools(context, scene_id, allow_overwrite=allow_overwrite)
    model = get_default_chat_model()

    # Create LangChain agent graph
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT
    )
```

### Subagent characteristics

- Created with `create_agent` (runnable graph)
- Use specialized tools only; no filesystem access
- Optional middleware: `HumanInTheLoopMiddleware` (approvals), `TodoListMiddleware` (self-planning)
- Context is injected via middleware; pipelines pass the shared `ProjectContext`

### Tool Access with ToolRuntime

Subagent tools should use `ToolRuntime` to access state, context, and store:

```python
from langchain.tools import tool, ToolRuntime

@tool
async def update_scene_summary(
    scene_id: str,
    summary: str,
    runtime: ToolRuntime
) -> str:
    """Update scene summary with provenance checking."""
    # Access project context from runtime
    context = runtime.context.project_context
    scene = context.get_scene(scene_id)

    # Check provenance for HITL
    if scene.annotations.summary_origin == "human":
        return "Requesting approval to overwrite human-authored summary"

    # Update with agent origin
    await context.update_scene_summary(scene_id, summary)
    return f"Updated summary for {scene_id}"
```

**Available via ToolRuntime:**
- `runtime.state` - Agent state (messages, custom fields)
- `runtime.context` - Immutable configuration (user IDs, project context)
- `runtime.store` - Persistent long-term memory
- `runtime.stream_writer` - Stream custom updates
- `runtime.config` - RunnableConfig for execution
- `runtime.tool_call_id` - ID of current tool call

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

**Critical rule:** Subagents interact with metadata ONLY via tools—never through direct file operations or context document reads.

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

### Context Injection via Middleware

Tools access the shared `ProjectContext` via `ToolRuntime`, which is injected by middleware:

```python
# Subagent factory
def create_scene_detailer_subagent(context: ProjectContext):
    """Create scene detailer with context injection."""
    tools = build_scene_tools()  # Generic tools, NOT scene-specific

    # Middleware injects shared context into runtime
    class ContextInjectionMiddleware:
        async def before_agent(self, state, runtime):
            # All tools can now access via runtime.context.project_context
            runtime.context.project_context = context
            return {}

    return create_agent(
        model=get_default_chat_model(),
        tools=tools,
        middleware=[ContextInjectionMiddleware()]
    )
```

**Key points:**
- Context is passed to subagent factory (captured via closure)
- Middleware injects same instance into `runtime.context`
- All concurrent subagents share the same `ProjectContext` instance
- Updates are immediately visible to all agents

---

## Tool Categories and Approval Policies

Tools are categorized by their operation type. Each category has default approval policies based on risk and provenance tracking.

### read_* Tools

**Purpose**: Retrieve data without modification

**Approval policy**: Always `permissive` (never require human approval)

**Examples**:
- `read_scene_overview`: Get scene metadata + transcript
- `read_character`: Get character bio/pronouns
- `read_glossary`: Search glossary entries
- `list_context_docs`: List available context documents

**Implementation**:

```python
from langchain_core.tools import tool

@tool
async def read_character(
    context: ProjectContext,
    character_id: str
) -> str:
    """Retrieves character metadata.

    Args:
        context: Project context.
        character_id: Character identifier.

    Returns:
        Character metadata as formatted string.
    """
    char = context.get_character(character_id)
    return f"""
Character: {char.name_tgt or char.name_src}
Pronouns: {char.pronouns}
Notes: {char.notes}
"""
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
- `add_glossary_entry`: Propose new glossary term (permissive)
- `add_character`: Create new character entry (strict)
- `add_route`: Create new route (strict)

**Implementation**:

```python
@tool(approval_policy="permissive")  # Low-risk, agent can add freely
async def add_glossary_entry(
    context: ProjectContext,
    term_src: str,
    term_tgt: str,
    notes: str
) -> str:
    """Adds a new glossary entry with provenance tracking.

    Args:
        context: Project context.
        term_src: Term in source language.
        term_tgt: Preferred target language rendering.
        notes: Translation guidance.

    Returns:
        Success message.
    """
    from datetime import date

    entry = GlossaryEntry(
        term_src=term_src,
        term_src_origin=f"agent:glossary_detailer:{date.today()}",
        term_tgt=term_tgt,
        term_tgt_origin=f"agent:glossary_detailer:{date.today()}",
        notes=notes,
        notes_origin=f"agent:glossary_detailer:{date.today()}"
    )

    context.glossary.append(entry)
    await context.save_glossary()
    return f"Added glossary entry: {term_src} → {term_tgt}"
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
- `update_character_bio`: Update character notes
- `update_scene_summary`: Revise scene summary
- `update_glossary_notes`: Improve glossary guidance

**Implementation**:

```python
@tool(approval_policy="standard")  # Provenance-based HITL
async def update_character_bio(
    context: ProjectContext,
    character_id: str,
    new_bio: str
) -> str:
    """Updates character biographical notes with provenance check.

    Args:
        context: Project context.
        character_id: Character identifier.
        new_bio: New biographical notes.

    Returns:
        Success message.

    Raises:
        ValueError: If character not found.
    """
    from datetime import date

    char = context.get_character(character_id)
    if char is None:
        raise ValueError(f"Character '{character_id}' not found")

    # Provenance check happens in LangChain HITL middleware via interrupt_on
    # If char.notes_origin == "human", execution pauses for approval
    # If char.notes_origin is None or "agent:*", proceeds automatically

    char.notes = new_bio
    char.notes_origin = f"agent:character_detailer:{date.today()}"

    await context.save_characters()
    return f"Updated bio for {char.name_tgt or char.name_src}"
```

**Guidelines**:
- Check provenance before updating: `if field_origin == "human": # pause for approval`
- Always update the corresponding `*_origin` field after modification
- Provide clear error messages for invalid inputs
- LangChain `HumanInTheLoopMiddleware` handles the actual approval pause

#### Conflict Detection in update_* Tools

When multiple subagents run concurrently, they might try to update the same field. `ProjectContext` implements **feedback-providing locks** to handle this intelligently:

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

**Purpose**: Remove entries from JSONL files

**Approval policy**:
- `standard`: Check entry-level provenance (if **any** field is human-authored, require approval)
- `strict`: Always require approval (safer default)

**Examples**:
- `delete_glossary_entry`: Remove a glossary term
- `delete_tag`: Remove a scene tag

**Implementation**:

```python
@tool(approval_policy="standard")  # Check if any field is human-authored
async def delete_glossary_entry(
    context: ProjectContext,
    term_src: str
) -> str:
    """Deletes a glossary entry after provenance check.

    Args:
        context: Project context.
        term_src: Source language term to delete.

    Returns:
        Success message.

    Raises:
        ValueError: If term not found.
    """
    entry = next(
        (e for e in context.glossary if e.term_src == term_src),
        None
    )
    if entry is None:
        raise ValueError(f"Glossary term '{term_src}' not found")

    # Check if ANY field has human origin
    has_human_origin = any([
        entry.term_src_origin == "human",
        entry.term_tgt_origin == "human",
        entry.notes_origin == "human"
    ])

    # If has_human_origin, LangChain HITL middleware pauses for approval
    # Otherwise, proceeds automatically

    context.glossary.remove(entry)
    await context.save_glossary()
    return f"Deleted glossary entry: {term_src}"
```

**Guidelines**:
- Check **all** `*_origin` fields in the entry
- If **any** field is `"human"`, require approval
- For `strict` policy, approval is always required regardless of provenance
- Validate that the entry exists before attempting deletion

---

## Provenance Tracking Best Practices

### Setting Origin on Creation

When creating new entries, always set `*_origin` for tracked fields:

```python
character = CharacterMetadata(
    id="new_char",
    name_src="新キャラ",
    name_src_origin="agent:character_detailer:2024-11-22",  # ✅ Set origin
    name_tgt="New Character",
    name_tgt_origin="agent:character_detailer:2024-11-22",  # ✅ Set origin
    pronouns="they/them",
    pronouns_origin="agent:character_detailer:2024-11-22",  # ✅ Set origin
    notes="Mysterious figure introduced in Chapter 3.",
    notes_origin="agent:character_detailer:2024-11-22"      # ✅ Set origin
)
```

### Updating Origin on Modification

When updating fields, always update the corresponding `*_origin`:

```python
# ✅ Good: Update both field and origin
scene.annotations.summary = new_summary
scene.annotations.summary_origin = f"agent:scene_detailer:{date.today()}"

# ❌ Bad: Update field without origin
scene.annotations.summary = new_summary
# Missing: summary_origin update!
```

### Origin String Format

Use consistent format: `"agent:<subagent_name>:<YYYY-MM-DD>"`

```python
from datetime import date

origin = f"agent:scene_detailer:{date.today()}"
# Example output: "agent:scene_detailer:2024-11-22"
```

**For human-set values** (rare in agent code):
```python
origin = "human"
```

### Checking Provenance for HITL

```python
@tool(approval_policy="standard")
async def update_field(context, value):
    entity = context.get_entity()

    # Check provenance
    if entity.field_origin == "human":
        # LangChain HITL middleware will pause here via interrupt_on
        # Human approves/rejects/edits the change
        pass
    elif entity.field_origin is None or entity.field_origin.startswith("agent:"):
        # Empty or agent-authored: proceed without approval
        pass

    # Update both field and origin
    entity.field = value
    entity.field_origin = f"agent:my_subagent:{date.today()}"
    await context.save()
```

---

## HITL Integration (LangChain)

Use LangChain `HumanInTheLoopMiddleware` on subagents when you need approvals for overwriting human-authored data. Pair it with a checkpointer so runs can pause and resume.

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import MemorySaver

graph = create_agent(
    model=model,
    tools=[
        read_character,
        update_character_bio,
    ],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "update_character_bio": {"allowed_decisions": ["approve", "edit", "reject"]},
                "read_character": False,
            }
        )
    ],
    checkpointer=MemorySaver(),
)
```

**How it works**:
1. Subagent proposes a tool call (e.g., `update_character_bio`).
2. Middleware checks `interrupt_on` and pauses if configured.
3. CLI/TUI collects decisions (approve/edit/reject) and resumes with the same thread_id.
4. Approved or edited actions execute; rejected actions produce tool feedback.

---

## Tool Access Control

Different subagents receive different tool subsets based on their role:

### Context Builder Tools

```python
context_builder_tools = [
    # Read tools (always available)
    read_scene_overview,
    read_character,
    read_location,
    read_glossary,
    read_route,
    list_context_docs,
    read_context_doc,

    # Write tools (context enrichment)
    write_scene_summary,
    update_character_bio,
    update_location_description,
    add_glossary_entry,
    update_glossary_entry,
    update_route_synopsis,
]
```

### Translator Tools

```python
translator_tools = [
    # Read tools only (translator consumes context, doesn't modify it)
    read_scene_overview,
    read_character,
    read_location,
    read_glossary,
    read_context_doc,

    # Write tool (translation output)
    write_translation,
]
```

### Editor Tools

```python
editor_tools = [
    # Read tools
    read_scene_overview,
    read_translation,
    read_glossary,
    read_style_guide,

    # QA tools
    record_style_check,
    record_consistency_check,
    record_quality_check,
    flag_for_retranslation,
]
```

**Principle**: Give subagents only the tools they need for their specific role.

---

## Example: Complete Tool Implementation

Here's a complete example of a well-designed tool with provenance tracking and HITL approval:

```python
from datetime import date
from langchain_core.tools import tool
from rentl_core.context import ProjectContext
from rentl_core.model.location import LocationMetadata


@tool(approval_policy="standard")
async def update_location_description(
    context: ProjectContext,
    location_id: str,
    new_description: str
) -> str:
    """Updates location description with provenance tracking and HITL approval.

    This tool allows the location_detailer subagent to enrich location metadata
    with atmospheric details, mood cues, and visual descriptions. Human-authored
    descriptions are protected via provenance checking.

    Args:
        context: Project context containing location metadata.
        location_id: Location identifier (e.g., "school_rooftop").
        new_description: New description text.

    Returns:
        Success message with location name.

    Raises:
        ValueError: If location_id not found in metadata.

    Examples:
        >>> await update_location_description(
        ...     context,
        ...     "school_rooftop",
        ...     "Windy rooftop with panoramic city view. Sunset glow."
        ... )
        "Updated description for Rooftop"
    """
    # Validate input
    if not new_description or not new_description.strip():
        raise ValueError("Description cannot be empty")

    # Get location (raises KeyError if not found)
    try:
        location = context.get_location(location_id)
    except KeyError:
        raise ValueError(
            f"Location '{location_id}' not found. "
            f"Available locations: {', '.join(context.locations.keys())}"
        )

    # Provenance check (LangChain HITL middleware handles approval pause)
    # If description_origin == "human", execution pauses for approval
    # If description_origin is None or "agent:*", proceeds automatically

    # Update field and origin
    location.description = new_description
    location.description_origin = f"agent:location_detailer:{date.today()}"

    # Persist changes
    await context.save_locations()

    # Return clear success message
    return f"Updated description for {location.name_tgt or location.name_src}"
```

**What makes this good**:
1. ✅ Clear docstring with examples
2. ✅ Input validation before processing
3. ✅ Helpful error messages with suggestions
4. ✅ Provenance tracking (updates both field and `*_origin`)
5. ✅ Async persistence (`await context.save_locations()`)
6. ✅ Clear return message for agent feedback

---

## Testing Tools

### Unit Test with Mock Context

```python
import pytest
from unittest.mock import AsyncMock
from rentl_core.context import ProjectContext
from rentl_core.model.location import LocationMetadata
from rentl_agents.tools.metadata import update_location_description


@pytest.mark.asyncio
async def test_update_location_description():
    # Create mock context
    context = AsyncMock(spec=ProjectContext)
    location = LocationMetadata(
        id="classroom",
        name_src="教室",
        name_tgt="Classroom",
        description="Old description",
        description_origin="agent:old_agent:2024-01-01"
    )
    context.get_location.return_value = location
    context.save_locations = AsyncMock()

    # Call tool
    result = await update_location_description(
        context,
        "classroom",
        "Bright classroom with afternoon sun streaming through windows."
    )

    # Assertions
    assert "Updated description for Classroom" in result
    assert location.description == "Bright classroom with afternoon sun streaming through windows."
    assert location.description_origin.startswith("agent:location_detailer:")
    context.save_locations.assert_called_once()


@pytest.mark.asyncio
async def test_update_location_description_not_found():
    context = AsyncMock(spec=ProjectContext)
    context.get_location.side_effect = KeyError("classroom")

    with pytest.raises(ValueError, match="Location 'classroom' not found"):
        await update_location_description(context, "classroom", "New desc")
```

---

## Summary

**Tool design checklist**:
- ✅ Choose correct category (read/add/update/delete)
- ✅ Set appropriate approval policy (permissive/standard/strict)
- ✅ Always update `*_origin` fields when modifying data
- ✅ Validate inputs and provide clear error messages
- ✅ Use async/await for I/O operations
- ✅ Write unit tests with mocked context
- ✅ Document with examples and clear docstrings

**Remember**:
- **read_* tools**: Always permissive
- **add_* tools**: Permissive for low-risk, strict for structural
- **update_* tools**: Standard (provenance check) by default
- **delete_* tools**: Standard or strict (safer)

See [AGENTS.md](../../AGENTS.md) for general coding guidelines and [SCHEMAS.md](../../SCHEMAS.md) for data format documentation.
