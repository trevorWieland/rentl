# Schema Changelog

This document tracks all schema migrations for `rentl.toml` config files. Each entry corresponds to a registered migration step in the migration registry.

**Machine-readable source of truth:** The migration registry in `packages/rentl-core/src/rentl_core/migrate.py` contains the actual transform functions. This changelog is the human-readable companion.

---

## 0.0.1 → 0.1.0

**Date:** 2026-02-09

**Description:** Initial migration demonstrating the migration system

**Changes:**
- Updates `project.schema_version` field from `0.0.1` to `0.1.0`
- Preserves all existing config fields (no data loss)

**Function:** `_migrate_0_0_1_to_0_1_0`

---
