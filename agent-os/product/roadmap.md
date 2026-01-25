# rentl Roadmap: From Playable to Professional-Grade

---

## v0.1: Playable Patch
**User Value:** "I can run a translation and get a playable patch"

**Primary Milestone:** End-to-end translation pipeline that produces a playable v1 translation in hours, not days.

**Key Differentiator:** First agentic localization pipeline that combines context intelligence, phase-based orchestration, and strict schemas—all with BYOK model support.

**Scope:**
- Complete 7-phase pipeline (ingest → context → source analysis → translate → QA → edit → export)
- One agent per phase (minimal but complete)
- CLI-first workflow (interactive setup → config → batch run)
- CSV/JSONL/TXT format support
- BYOK OpenAI-compatible endpoint configuration
- Basic QA checks + schema validation
- Progress observability by phase/line/scene
- Export patch output
- Functional onboarding (you can get it working)

**Success Criteria:**
- Produces higher-quality output than simple MTL
- End-to-end pipeline runs deterministically
- Users can complete a full project without expert intervention

---

## v0.2: Quality Leap
**User Value:** "I can run a translation and get a decent patch, with the same effort"

**Primary Milestone:** Translation quality jumps from "playable but rough" to "genuinely decent" through multi-agent teams per phase.

**Key Differentiator:** Each phase becomes a cohesive "team" of agents working together—smarter context analysis, more sophisticated translation, richer QA—rather than a single sample agent.

**Scope:**
- Multiple agents per phase (tuned based on v0.1 experience)
- Context team: scene summarization + route tracking + character consistency
- Source analysis team: idiom detector + reference finder + cultural note generator
- Translation team: multiple translators with different approaches (literal → liberal) + consensus selection
- QA team: style checker + consistency validator + cultural appropriateness reviewer
- Edit team: smart retranslation + pattern-based fixes + style alignment
- Richer QA checks (beyond basic style)
- Enhanced QA reporting with granular issue categorization
- Improved agent iteration visibility and control
- Functional onboarding refinements

**Success Criteria:**
- First-pass translations are noticeably higher quality than v0.1
- QA catches issues that v0.1 missed
- Translation quality feels "decent" rather than "playable but rough"

---

## v0.3: Scale & Ecosystem
**User Value:** "I can run a translation and get multiple decent patches, and it works for my game out of the box (for popular engines)"

**Primary Milestone:** Multi-language support and game engine integration unlock localization at scale.

**Key Differentiator:** One core context setup translates into N languages, and your favorite game engine works out of the box—no custom schema wrangling.

**Scope:**
- Multi-language batch orchestration (run N languages in parallel)
- Language-specific profiles and settings
- Cost controls and token usage tracking across languages
- Adapter interfaces framework
- Engine-specific adapters: RPG Maker, Ren'Py, Kirikiri
- Engine-specific schemas and import/export formats
- Batch management for large multi-language projects
- Multi-language progress tracking and reporting
- Functional onboarding refinements

**Success Criteria:**
- Users can translate one script into 3+ languages in one workflow
- RPG Maker, Ren'Py, or Kirikiri projects work out of the box
- Multi-language runs complete predictably with clear cost visibility

---

## v0.4: UX Polish
**User Value:** "I can run a translation and get multiple decent patches, and it works for my game out of the box (for popular engines), all from a convenient and nice TUI"

**Primary Milestone:** Complete TUI makes the entire workflow accessible without CLI mastery.

**Key Differentiator:** From setup to shipping, everything is doable from a polished, intuitive interface—no more terminal command memorization.

**Scope:**
- Complete TUI surface (beyond read-only status viewer)
- Interactive setup wizard (guided configuration, context input, model selection)
- Real-time progress monitoring with visual phase tracking
- QA review interface (view flagged lines, add reviewer notes inline)
- Edit workflow UI (triage issues, trigger edit cycles, preview fixes)
- Multi-language batch management UI
- Project and configuration management screens
- Visual dashboards for QA reporting and iteration analytics
- Settings and preferences interface
- Functional onboarding refinements

**Success Criteria:**
- Users can complete end-to-end workflows using only the TUI
- Non-technical users can run multi-language batches without CLI knowledge
- TUI feels polished and intuitive (not just functional)

---

## v1.0: Professional-Grade Tooling
**User Value:** "This is professional-grade tooling"

**Primary Milestone:** rentl reaches feature parity with enterprise CAT tools while maintaining the agility and accessibility that define it.

**Key Differentiator:** The combination of agentic automation, professional-grade reliability, rapid iteration, and delightful onboarding makes rentl a viable alternative to enterprise CAT stacks for small teams and a serious upgrade for fan translators.

**Scope:**
- **CAT-grade feature parity:**
  - Translation memory (TM) with fuzzy matching and reuse
  - Glossary/term locking with enforcement across all translation passes
  - Comprehensive QA suites (terminology, consistency, formatting, completeness)
  - Advanced reporting dashboards with iteration analytics
- **Rapid hotfix loop:**
  - Issue triage workflow (automated issue detection → human review → fix routing)
  - Editor agent applies fixes consistently across similar lines
  - Patch generation within minutes for targeted fixes
- **Reliability and stability:**
  - 99%+ end-to-end pipeline success rate
  - Strong stability guarantees for schemas and CLI
  - Clear deprecation paths and migration guides
  - Comprehensive error recovery and rollback
- **Delightful onboarding:**
  - Guided setup wizard with best-practice templates
  - Contextual help and documentation in the TUI
  - Project templates for different game types (visual novels, RPGs, etc.)
  - Partner-studio shared configs and templates
- **Operational maturity:**
  - Benchmarking framework with quality rubrics (accuracy, style fidelity, consistency)
  - Example/benchmark repository with real-game demos
  - Contributor-friendly architecture and documentation

**Success Criteria:**
- Feature parity with core CAT tool capabilities (TM, glossaries, QA suites, reporting)
- Rapid hotfix loop works reliably (issue → fix → patch in <10 minutes)
- v1.0 experience feels professional, reliable, and delightful
- Small pro teams can adopt rentl as their primary localization pipeline
- 100+ GitHub stars (directional community signal)

---

## Version Identity Summary

| Version | User Promise | Primary Leap |
|---------|--------------|--------------|
| **v0.1** | "Playable patch" | End-to-end pipeline works |
| **v0.2** | "Decent quality" | Multi-agent teams per phase |
| **v0.3** | "Scale & ecosystem" | Multi-language + engine adapters |
| **v0.4** | "Great UX" | Complete TUI workflow |
| **v1.0** | "Professional-grade" | CAT parity + reliability + polish |

---

## Post-v1.0 Future Directions (Out of Scope)

- Expanded adapter ecosystem (more engines, deeper integration)
- Hosted service layer with team collaboration features
- Advanced agent orchestration and auto-tuning
- Community marketplace for agent configurations and templates
- Enterprise features (SSO, audit logs, advanced permissions)
- Docker Compose support for collaborative/production deployments with hosted alternatives (PostgreSQL, hosted vector DB, etc.)
