# Audit Log

Running record of all task audits, demo runs, and spec audits.
Future auditors: check this log for regressions and patterns.

---

- **Task 2** (round 1): PASS — Endpoint preset updates are complete and tests pass.
- **Task 3** (round 1): PASS — Local preset prompt behavior and updated CLI model references are verified by passing unit/integration tests.
- **Task 4** (round 1): PASS — Required `model_id` enforcement is implemented in runtime/harness configs and all scoped unit/integration tests pass.
- **Task 5** (round 1): PASS — Documentation/model-hint updates are complete and benchmark-focused unit/integration tests pass.
- **Demo** (run 1): PASS — All 5 [RUN] steps pass: presets produce correct models, Local prompts for model, configs reject missing model_id, no stale model strings in production code (5 run, 0 verified)
- **Spec Audit** (round 1): FAIL — Rubric `5/4/3/5/5`, non-negotiables 4/5 PASS, demo latest PASS (run 1), fix-now count 2
- **Task 4** (round 2): PASS — `model_id` is required in runtime/harness configs with strict `Field` annotations, and all scoped Task 4 unit/integration tests pass (54/54).
- **Task 5** (round 2): PASS — Stale model names were removed from `agent-os/product/roadmap.md`, and repo scan confirms no stale model strings outside spec-history docs.
- **Demo** (run 2): PASS — All 5 [RUN] steps pass post-audit fixes: presets correct, Local prompts for model, configs reject missing model_id, zero stale strings in project code (5 run, 0 verified)
- **Spec Audit** (round 2): FAIL — Rubric `5/4/3/5/5`, non-negotiables 5/5 PASS, demo latest PASS (run 2), fix-now count 3
- **Task 4** (round 3): PASS — Schema field annotations in runtime/harness satisfy strict typing, and focused validation tests for required `model_id` pass (2/2).
- **Task 5** (round 3): PASS — README Local/default-model wording and quality test assertion text are updated, with no stale model strings outside historical spec docs.
- **Demo** (run 3): PASS — All 5 [RUN] steps pass post-audit round 2 fixes: presets correct, Local prompts for model, configs reject missing model_id, zero stale strings outside spec history (5 run, 0 verified)
