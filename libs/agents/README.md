# rentl-agents: Tools and Subagent Implementation Guide

This document provides implementation guidance for building tools and subagents for rentl's translation pipeline.

---

## Overview

The `rentl-agents` package contains:

- **Subagents**: Specialized agents for context building, translation, and editing
- **Tools**: LangChain tools with HITL approval gating
- **LLM backends**: Wrappers for OpenAI-compatible endpoints
- **Graph engine**: DeepAgents orchestration setup

**File structure**:
```
libs/agents/src/rentl_agents/
  backends/
    base.py           # LLM backend abstractions
    openai_like.py    # ChatOpenAI wrapper
  graph/
    engine.py         # DeepAgents setup and middleware
  subagents/
    *.py              # Individual subagent implementations
  tools/
    scene.py          # Scene-related tools
    metadata.py       # Character/glossary/route tools
```

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

    # Provenance check happens in DeepAgents middleware via interrupt_on
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
- DeepAgents `interrupt_on` middleware handles the actual approval pause

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

    # If has_human_origin, DeepAgents middleware pauses for approval
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
        # DeepAgents middleware will pause here via interrupt_on
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

## DeepAgents Integration

### Tool Registration with interrupt_on

Tools are registered with DeepAgents using the `interrupt_on` parameter for HITL approval:

```python
from deepagents import create_deep_agent

# Define tools with approval policies
tools = [
    read_character,           # approval_policy="permissive" (implicit)
    update_character_bio,     # approval_policy="standard"
    add_glossary_entry,       # approval_policy="permissive"
    delete_glossary_entry,    # approval_policy="standard"
]

# Create agent with HITL gating
agent = create_deep_agent(
    model=llm,
    tools=tools,
    interrupt_on={
        "update_character_bio": {
            "allowed_decisions": ["approve", "edit", "reject"]
        },
        "delete_glossary_entry": {
            "allowed_decisions": ["approve", "reject"]
        }
    },
    middleware=[
        TodoListMiddleware(),
        FilesystemMiddleware(),
        SubAgentMiddleware()
    ]
)
```

**How it works**:
1. Agent calls `update_character_bio` tool
2. DeepAgents checks if tool is in `interrupt_on` dict
3. If yes, execution pauses and waits for human decision
4. Human approves/edits/rejects via CLI or web UI
5. Execution resumes with the decision

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

    # Provenance check (DeepAgents middleware handles approval pause)
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
