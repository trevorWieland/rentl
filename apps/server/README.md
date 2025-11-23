# rentl-server: Web UI and REST API (v1.3)

> **Status**: Placeholder for v1.3. Not implemented in v1.0.

---

## Purpose (Planned)

`rentl-server` will provide:

- Web-based translation review interface
- HITL approval dashboard
- Visual context browsing (characters, locations, glossary)
- REST API for programmatic access
- Real-time collaboration tools

**Target users**: Teams reviewing translations, approving agent changes, and managing projects through a web interface.

---

## Scope (Planned for v1.3)

### In Scope

- Web UI for translation review (side-by-side source/target)
- HITL approval interface (approve/edit/reject agent changes)
- Visual browsing of metadata (characters, glossary, routes)
- REST API for project management
- WebSocket support for real-time updates
- User authentication and project permissions

### Out of Scope

- Pipeline execution (still handled via CLI or API)
- Agent logic (belongs in `rentl-agents`)
- Primary editing interface (CLI is primary; web is supplementary)

---

## Planned Architecture (v1.3)

### Technology Stack

**Backend**:
- **FastAPI**: REST API and WebSocket server
- **SQLAlchemy**: Optional database for user sessions
- **Pydantic**: Request/response validation
- **rentl-core**: Data models and project context

**Frontend** (TBD):
- **React** or **Svelte**: UI framework
- **TailwindCSS**: Styling
- **WebSocket client**: Real-time updates

### API Structure

```
/api/
  /projects                   # List projects
  /projects/{id}              # Project details
  /projects/{id}/scenes       # List scenes
  /projects/{id}/scenes/{sid} # Scene details
  /projects/{id}/metadata     # Browse metadata
  /approvals                  # Pending HITL approvals
  /approvals/{id}/approve     # Approve change
  /approvals/{id}/reject      # Reject change
  /ws                         # WebSocket for real-time updates
```

---

## Planned Features

### Translation Review UI

- Side-by-side source/target display
- Highlight QA check failures
- Inline editing with provenance tracking
- Filter by scene, route, or character

### HITL Approval Dashboard

- List pending approvals (character updates, glossary additions, etc.)
- Show diff (before/after) for each change
- Approve, edit, or reject with comments
- Batch approval for trusted agents

### Metadata Browser

- Visual character profiles with bios/pronouns
- Glossary search and editing
- Route timeline visualization
- Context doc viewer

---

## Development Notes (v1.0)

**Current status**: Placeholder directory with minimal structure.

**When to implement**: After v1.0 CLI is stable and users have requested web UI features.

**Design priorities**:
1. **Read-only first**: Start with viewing translations and metadata
2. **HITL approval second**: Add interactive approval interface
3. **Editing last**: Full editing capabilities (CLI remains primary)

---

## Future Considerations

### Multi-User Support

- User authentication and project permissions
- Team collaboration features
- Comment threads on translations
- Change history and audit logs

### Advanced Features

- Translation memory integration
- Terminology consistency highlighting
- Cross-scene diff view
- Export to various formats (Translator++, TMX, etc.)

---

## Dependencies (Planned)

**Backend**:
- `fastapi`: REST API framework
- `uvicorn`: ASGI server
- `sqlalchemy`: Optional database
- `rentl-core`: Data models

**Frontend**:
- TBD based on final design decisions

---

## Summary

`rentl-server` is planned for **v1.3** to provide:
- Web-based translation review
- HITL approval dashboard
- REST API for external tools

**Not a priority for v1.0**—CLI is the primary interface. Web UI will be added based on user feedback and team collaboration needs.

See [README.md](../../README.md) for the v1.3 roadmap.
