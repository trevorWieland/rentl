spec_id: s0.1.26
issue: https://github.com/trevorWieland/rentl/issues/27
version: v0.1

# Plan: Standards Review — Declarative Agent Config

## Decision Record

The declarative agent config system has been built incrementally across specs s0.1.14 (Agent Runtime Scaffold), s0.1.15 (Context Agent), and s0.1.16 (Pretranslation Agent). Each spec added config patterns that are now consistent but undocumented as a formal standard. This spec codifies those patterns so future agents and auditors have a single reference document, then audits existing profiles to ensure compliance.

## Tasks

- [x] Task 1: Save Spec Documentation
  - Write spec.md, plan.md, demo.md, standards.md, references.md
  - Commit on issue branch and push
- [x] Task 2: Write the Declarative Agent Config Standard
  - Create `agent-os/standards/architecture/declarative-agent-config.md`
  - Sections: Agent Profile Schema, TOML File Structure, Layered Prompt System, Template Variable Registry, Tool Registration & Access Control, Model Hints, Orchestration Config, Pipeline Phase Config
  - Each section references actual Pydantic fields from `rentl_schemas/agents.py` and `rentl_schemas/config.py`
  - Add entry to `agent-os/standards/index.yml` under `architecture`
  - Test expectations: standard document parses cleanly, index.yml is valid YAML
  - [x] Fix: Align tool-name validation rule in the standard with actual schema enforcement; `declarative-agent-config.md` claims `^[a-z_]+$`, but `ToolAccessConfig.validate_allowed_tools` accepts names where `name.replace("_", "").isalnum()` (`agent-os/standards/architecture/declarative-agent-config.md:81`, `packages/rentl-schemas/src/rentl_schemas/agents.py:142`) (audit round 1)
- [ ] Task 3: Audit Existing Agent Profiles Against Standard
  - Load all agent TOML profiles via `discover_agent_profiles()`
  - Cross-reference each profile field against the standard
  - Document deviations with file path, field, expected vs actual
  - Record findings in a structured audit section in this plan
  - Test expectations: profile loading succeeds for all agents
- [ ] Task 4: Fix Deviations and Verify No Regressions
  - Fix any deviations found in Task 3
  - Verify fixes don't change runtime behavior (existing tests pass)
  - Run `make check` to confirm task gate passes
  - Test expectations: all existing tests pass, no behavior changes
