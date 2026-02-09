# Demo: Config Schema Versioning + Migrate

Config evolves as rentl evolves. When a user upgrades rentl, their existing `rentl.toml` should just work — no manual edits, no guessing what changed. This demo proves that the migration system handles version transitions smoothly and transparently.

## Steps

1. **Create an outdated config** — write a `rentl.toml` with `schema_version = { major = 0, minor = 0, patch = 1 }` (an older format). Show it loads and is recognized as outdated.
   - Expected: the config is parseable but has an older schema version than current.

2. **Dry-run migration** — run `rentl migrate --dry-run` and show the planned changes without modifying the file.
   - Expected: output lists source version (0.0.1), target version (0.1.0), and each migration step's description. No file is modified.

3. **Run migration** — run `rentl migrate`.
   - Expected: the original file is backed up to `rentl.toml.bak`, the migrated file has the current `schema_version`, and the output summarizes what changed.

4. **Auto-migrate on load** — restore the old config (from backup), then run a config-loading command (e.g. `rentl doctor`). Verify the config is auto-migrated, a backup is created, and the command succeeds with the migrated config.
   - Expected: `rentl doctor` succeeds, `rentl.toml.bak` exists, and `rentl.toml` now has the current schema version.

5. **Already current** — run `rentl migrate` on the already-migrated config.
   - Expected: output reports "already up to date" and makes no changes. No new backup is created.

## Results

(Appended by run-demo — do not write this section during shaping)
